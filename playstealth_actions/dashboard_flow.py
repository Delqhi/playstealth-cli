"""Dashboard Flow Orchestrator for complete survey automation loop."""
import asyncio
import time
from playwright.async_api import async_playwright
from .stealth_profile import generate_profile, apply_stealth_profile
from .pacing_controller import acquire_session_lock, release_session_lock, is_within_active_hours, inter_survey_break, human_reading_delay
from .survey_screener import check_disqualification, handle_disqualification
from .ban_risk_monitor import calculate_ban_risk
from .persona_manager import get_persona
from .consistency_validator import record_answer, validate_consistency, detect_straight_lining
from .telemetry import log_event, generate_session_id
from .human_behavior import human_click
from .answer_strategies import get_strategy

async def _dynamic_resolve(page, query: str, max_retries: int = 2):
    """Simple dynamic resolver fallback."""
    from .smart_actions import SmartClickAction
    for _ in range(max_retries):
        try:
            loc = page.locator(f'text={query}')
            if await loc.count() > 0:
                return loc.first
        except Exception:
            pass
    return None

async def run_dashboard_flow(
    dashboard_url: str,
    login_selectors: dict = None,
    max_surveys: int = 3,
    max_steps_per_survey: int = 15,
    persona_name: str = "default",
    strategy_name: str = "persona",
    strategy_persona: str = "neutral"
):
    """Complete loop: Login → Survey-Scan → Screening → Completion → Break → Repeat."""
    if not acquire_session_lock():
        print("🔒 Session lock active. Parallel runs blocked for safety.")
        return

    if not is_within_active_hours():
        print("🌙 Outside active hours (8-22h). Exiting to mimic human rhythm.")
        release_session_lock()
        return

    risk = calculate_ban_risk()
    if risk["status"] == "critical":
        print(f"🚨 Ban risk critical ({risk['risk']}%). Cooldown enforced.")
        release_session_lock()
        return

    session_id = generate_session_id()
    persona = get_persona(persona_name)
    strategy = get_strategy(strategy_name, persona=strategy_persona)
    completed_surveys = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        profile = generate_profile("win_chrome")
        ctx = await browser.new_context(
            user_agent=profile["ua"], 
            locale=profile["languages"][0],
            timezone_id=profile["timezone"], 
            viewport={"width": 1920, "height": 1080}
        )
        await apply_stealth_profile(ctx, profile)
        page = await ctx.new_page()

        try:
            # 1. Login
            print("🔐 Logging in...")
            await page.goto(dashboard_url, wait_until="domcontentloaded")
            if login_selectors and login_selectors.get("email_val"):
                email_loc = await _dynamic_resolve(page, login_selectors["email"])
                if email_loc:
                    await email_loc.fill(login_selectors["email_val"])
                pass_loc = await _dynamic_resolve(page, login_selectors["password"])
                if pass_loc:
                    await pass_loc.fill(login_selectors["password_val"])
                submit_loc = await _dynamic_resolve(page, login_selectors["submit"])
                if submit_loc:
                    await human_click(page, submit_loc)
                    await page.wait_for_load_state("networkidle")
                log_event(session_id, "login_success", platform="dashboard")

            # 2. Main Loop
            while completed_surveys < max_surveys:
                if not is_within_active_hours():
                    print("🌙 Active hours ended. Stopping gracefully.")
                    break

                print(f"\n📋 Scanning dashboard for survey {completed_surveys+1}/{max_surveys}...")
                await page.goto(dashboard_url, wait_until="domcontentloaded")
                await page.wait_for_load_state("networkidle")

                # Finde verfügbare Umfrage
                survey_loc = await _dynamic_resolve(page, "start", max_retries=2)
                if not survey_loc or await survey_loc.count() == 0:
                    print("⏳ No surveys available. Waiting...")
                    await inter_survey_break(min_min=10, max_min=30)
                    continue

                await human_click(page, survey_loc)
                await page.wait_for_load_state("networkidle")
                log_event(session_id, "survey_start", platform="dashboard")

                # 3. Screening Phase
                print("🔍 Screening phase (first 3 steps)...")
                disqualified = False
                for step in range(1, 4):
                    await asyncio.sleep(1.5)
                    if await check_disqualification(page):
                        await handle_disqualification(page, session_id, "dashboard", dashboard_url)
                        disqualified = True
                        break
                    await page.evaluate(f"window.scrollTo(0, {step * 200})")
                    next_btn = await _dynamic_resolve(page, "weiter")
                    if next_btn:
                        await human_click(page, next_btn)

                if disqualified:
                    await inter_survey_break(min_min=2, max_min=8)
                    continue

                # 4. Main Completion
                print("✅ Screening passed. Completing survey...")
                recent_answers = []
                for step in range(1, max_steps_per_survey + 1):
                    start = time.perf_counter()
                    log_event(session_id, "step_start", platform="dashboard", step_index=step)

                    # Frage extrahieren
                    q_text = "Unknown"
                    try:
                        q_loc = await _dynamic_resolve(page, "frage")
                        if q_loc:
                            q_text = await q_loc.inner_text(timeout=3000)
                    except Exception:
                        pass

                    await human_reading_delay(q_text)

                    # Optionen parsen & Strategy anwenden
                    opts_loc = await page.locator("input[type='radio'], input[type='checkbox'], .option, [role='radio']").all()
                    opts_text = [await o.inner_text() for o in opts_loc] if opts_loc else []
                    chosen_idx = await strategy.choose(q_text, len(opts_text), opts_text)

                    # Consistency & Straight-Line Check
                    chosen_answer = opts_text[chosen_idx] if opts_text else f"idx_{chosen_idx}"
                    await record_answer(q_text, chosen_answer, f"survey_{completed_surveys}")
                    recent_answers.append(chosen_answer)

                    cons = await validate_consistency(q_text, chosen_answer, persona)
                    if not cons["consistent"]:
                        print(f"⚠️ Consistency warning: {cons['contradictions']}")
                        log_event(session_id, "consistency_warning", platform="dashboard", step_index=step, metadata={"issues": cons["contradictions"]})

                    if await detect_straight_lining(recent_answers, threshold=4):
                        print("⚠️ Straight-lining detected. Varying answer.")
                        chosen_idx = (chosen_idx + 1) % max(1, len(opts_text))
                        log_event(session_id, "straight_line_blocked", platform="dashboard", step_index=step)

                    # Antwort klicken & weiter
                    if opts_loc and 0 <= chosen_idx < len(opts_loc):
                        await human_click(page, opts_loc[chosen_idx])
                    
                    next_btn = await _dynamic_resolve(page, "weiter")
                    if next_btn:
                        await human_click(page, next_btn)

                    dur = (time.perf_counter() - start) * 1000
                    log_event(session_id, "step_end", platform="dashboard", step_index=step, duration_ms=dur, success=True)

                    if await check_disqualification(page):
                        await handle_disqualification(page, session_id, "dashboard", dashboard_url)
                        break

                completed_surveys += 1
                log_event(session_id, "survey_complete", platform="dashboard")
                print(f"✅ Survey {completed_surveys} finished.")
                await inter_survey_break()

        except Exception as e:
            print(f"❌ Dashboard flow error: {e}")
            log_event(session_id, "flow_error", platform="dashboard", error_code=str(e))
        finally:
            await browser.close()
            release_session_lock()
            print("🔓 Session lock released. Flow ended.")
