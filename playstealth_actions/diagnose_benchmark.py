"""
Diagnose Benchmark - Automated Stealth Testing.

This module provides automated testing against common bot detection techniques,
including checks inspired by CreepJS and SannySoft.
"""
import json
from datetime import datetime
from typing import Dict, Any, List

try:
    from playwright.async_api import Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


async def run_stealth_audit(page: Page) -> Dict[str, Any]:
    """
    Run comprehensive stealth audit on the current page.
    
    Tests for common bot detection vectors:
    - navigator.webdriver property
    - navigator.plugins presence
    - navigator.languages configuration
    - WebGL vendor/renderer information
    - Canvas fingerprinting detection
    - Timezone configuration
    - Permissions API availability
    - Chrome runtime (headless indicator)
    
    Args:
        page: Playwright Page instance
        
    Returns:
        Dictionary with audit results for each check
    """
    if not PLAYWRIGHT_AVAILABLE:
        raise ImportError("Playwright is required for stealth auditing")
    
    js_audit = """
    () => {
        const results = {};
        
        // Check 1: navigator.webdriver
        results.webdriver = navigator.webdriver === undefined || navigator.webdriver === false;
        results.webdriver_value = navigator.webdriver;
        
        // Check 2: navigator.plugins
        results.plugins = navigator.plugins.length > 0;
        results.plugins_count = navigator.plugins.length;
        
        // Check 3: navigator.languages
        results.languages = Array.isArray(navigator.languages) && navigator.languages.length > 0;
        results.languages_list = navigator.languages || [];
        
        // Check 4: WebGL context and renderer info
        try {
            const canvas = document.createElement('canvas');
            const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
            if (gl) {
                const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
                if (debugInfo) {
                    results.webgl_vendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
                    results.webgl_renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
                    results.webgl_ok = true;
                } else {
                    results.webgl_ok = false;
                    results.webgl_error = "WEBGL_debug_renderer_info extension not available";
                }
            } else {
                results.webgl_ok = false;
                results.webgl_error = "WebGL context not available";
            }
        } catch(e) {
            results.webgl_ok = false;
            results.webgl_error = e.message;
        }
        
        // Check 5: Canvas fingerprinting
        try {
            const canvas = document.createElement('canvas');
            canvas.width = 200;
            canvas.height = 50;
            const ctx = canvas.getContext('2d');
            ctx.textBaseline = 'top';
            ctx.font = '14px Arial';
            ctx.fillText('stealth_test', 2, 2);
            results.canvas_hash = canvas.toDataURL().slice(-30);
            results.canvas_ok = true;
        } catch(e) {
            results.canvas_ok = false;
            results.canvas_error = e.message;
        }
        
        // Check 6: Timezone
        try {
            results.timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
            results.timezone_ok = true;
        } catch(e) {
            results.timezone_ok = false;
            results.timezone_error = e.message;
        }
        
        // Check 7: Permissions API
        results.permissions = typeof navigator.permissions !== 'undefined';
        
        // Check 8: Chrome runtime (headless indicator)
        results.chrome_runtime = typeof chrome !== 'undefined' && typeof chrome.runtime !== 'undefined';
        
        // Check 9: navigator.platform
        results.platform = navigator.platform;
        
        // Check 10: navigator.hardwareConcurrency
        results.hardware_concurrency = navigator.hardwareConcurrency;
        
        // Check 11: navigator.deviceMemory
        results.device_memory = navigator.deviceMemory;
        
        // Check 12: outerWidth/outerHeight (headless indicator)
        results.outer_width = window.outerWidth;
        results.outer_height = window.outerHeight;
        results.screen_width = window.screen.width;
        results.screen_height = window.screen.height;
        
        return results;
    }
    """
    
    return await page.evaluate(js_audit)


async def diagnose_benchmark(page: Page) -> Dict[str, Any]:
    """
    Run full benchmark and calculate stealth score.
    
    Args:
        page: Playwright Page instance
        
    Returns:
        Dictionary with score, warnings, and detailed results
    """
    if not PLAYWRIGHT_AVAILABLE:
        raise ImportError("Playwright is required for benchmark diagnostics")
    
    audit = await run_stealth_audit(page)
    
    # Define critical checks and their weights
    checks = {
        "webdriver": {"passed": audit.get("webdriver", False), "critical": True, "message": "navigator.webdriver leak detected"},
        "plugins": {"passed": audit.get("plugins", False), "critical": True, "message": "Empty navigator.plugins (bot indicator)"},
        "languages": {"passed": audit.get("languages", False), "critical": True, "message": "Missing navigator.languages"},
        "webgl_ok": {"passed": audit.get("webgl_ok", False), "critical": False, "message": "WebGL context failed or blocked"},
        "canvas_ok": {"passed": audit.get("canvas_ok", False), "critical": False, "message": "Canvas fingerprint blocked or errored"},
        "timezone_ok": {"passed": audit.get("timezone_ok", False), "critical": True, "message": "Timezone resolution failed"},
        "permissions": {"passed": audit.get("permissions", False), "critical": False, "message": "Permissions API missing"},
        "chrome_runtime": {"passed": audit.get("chrome_runtime", False), "critical": True, "message": "chrome.runtime missing (headless Chrome indicator)"},
    }
    
    # Calculate score
    total_weight = sum(2 if c["critical"] else 1 for c in checks.values())
    earned_weight = sum(
        (2 if c["critical"] else 1) 
        for c in checks.values() 
        if c["passed"]
    )
    
    score_percentage = round((earned_weight / total_weight) * 100, 1) if total_weight > 0 else 0
    
    # Generate warnings
    warnings = [c["message"] for c in checks.values() if not c["passed"]]
    critical_warnings = [c["message"] for c in checks.values() if not c["passed"] and c["critical"]]
    
    # Determine overall status
    if len(critical_warnings) > 0:
        status = "FAIL"
    elif len(warnings) > 0:
        status = "WARN"
    else:
        status = "PASS"
    
    return {
        "timestamp": datetime.now().isoformat(),
        "status": status,
        "stealth_score": f"{earned_weight}/{total_weight}",
        "percentage": score_percentage,
        "total_checks": len(checks),
        "passed_checks": sum(1 for c in checks.values() if c["passed"]),
        "warnings": warnings,
        "critical_warnings": critical_warnings,
        "raw_audit": audit,
    }


async def check_webgl_leaks(page: Page) -> Dict[str, Any]:
    """
    Specific check for WebGL fingerprinting leaks.
    
    Args:
        page: Playwright Page instance
        
    Returns:
        Dictionary with WebGL-specific audit results
    """
    audit = await run_stealth_audit(page)
    
    return {
        "timestamp": datetime.now().isoformat(),
        "webgl_available": audit.get("webgl_ok", False),
        "vendor": audit.get("webgl_vendor", "Unknown"),
        "renderer": audit.get("webgl_renderer", "Unknown"),
        "error": audit.get("webgl_error"),
        "looks_suspicious": audit.get("webgl_vendor", "").startswith("Google Inc.") and "ANGLE" not in audit.get("webgl_renderer", ""),
    }


async def check_timezone_consistency(page: Page, expected_ip_timezone: str = None) -> Dict[str, Any]:
    """
    Check timezone consistency between browser and IP geolocation.
    
    Args:
        page: Playwright Page instance
        expected_ip_timezone: Expected timezone based on IP (optional)
        
    Returns:
        Dictionary with timezone audit results
    """
    audit = await run_stealth_audit(page)
    
    browser_tz = audit.get("timezone", "Unknown")
    
    result = {
        "timestamp": datetime.now().isoformat(),
        "browser_timezone": browser_tz,
        "ip_timezone": expected_ip_timezone,
        "matches": browser_tz == expected_ip_timezone if expected_ip_timezone else None,
        "timezone_ok": audit.get("timezone_ok", False),
    }
    
    if expected_ip_timezone and browser_tz != expected_ip_timezone:
        result["warning"] = f"Timezone mismatch: Browser={browser_tz}, IP={expected_ip_timezone}"
    
    return result


async def check_headless_indicators(page: Page) -> Dict[str, Any]:
    """
    Check for common headless browser indicators.
    
    Args:
        page: Playwright Page instance
        
    Returns:
        Dictionary with headless detection results
    """
    audit = await run_stealth_audit(page)
    
    indicators = []
    
    # Check chrome.runtime
    if not audit.get("chrome_runtime", False):
        indicators.append("chrome.runtime missing")
    
    # Check outerWidth/outerHeight vs screen dimensions
    outer_w = audit.get("outer_width", 0)
    outer_h = audit.get("outer_height", 0)
    screen_w = audit.get("screen_width", 0)
    screen_h = audit.get("screen_height", 0)
    
    if outer_w == 0 or outer_h == 0:
        indicators.append("outerWidth/outerHeight is 0 (common in headless)")
    elif outer_w != screen_w or outer_h != screen_h:
        # This is normal for non-fullscreen windows, but worth noting
        pass
    
    # Check webdriver
    if audit.get("webdriver_value") is not None and audit.get("webdriver_value") is not False:
        indicators.append(f"navigator.webdriver = {audit.get('webdriver_value')}")
    
    # Check plugins
    if audit.get("plugins_count", 0) == 0:
        indicators.append("No navigator.plugins (common in headless)")
    
    return {
        "timestamp": datetime.now().isoformat(),
        "is_likely_headless": len(indicators) > 0,
        "indicators_found": indicators,
        "indicator_count": len(indicators),
        "raw_data": {
            "chrome_runtime": audit.get("chrome_runtime"),
            "outer_dimensions": f"{outer_w}x{outer_h}",
            "screen_dimensions": f"{screen_w}x{screen_h}",
            "webdriver": audit.get("webdriver_value"),
            "plugins_count": audit.get("plugins_count"),
        }
    }


async def full_stealth_check(page: Page) -> Dict[str, Any]:
    """
    Run complete stealth diagnostic suite.
    
    Combines all checks into a comprehensive report.
    
    Args:
        page: Playwright Page instance
        
    Returns:
        Comprehensive diagnostic report
    """
    benchmark = await diagnose_benchmark(page)
    webgl = await check_webgl_leaks(page)
    headless = await check_headless_indicators(page)
    
    return {
        "timestamp": datetime.now().isoformat(),
        "overall_status": benchmark["status"],
        "stealth_score": benchmark["stealth_score"],
        "percentage": benchmark["percentage"],
        "benchmark": benchmark,
        "webgl_check": webgl,
        "headless_check": headless,
        "recommendations": _generate_recommendations(benchmark, webgl, headless),
    }


def _generate_recommendations(
    benchmark: Dict[str, Any], 
    webgl: Dict[str, Any],
    headless: Dict[str, Any]
) -> List[str]:
    """Generate actionable recommendations based on audit results."""
    recommendations = []
    
    if benchmark.get("critical_warnings"):
        for warning in benchmark["critical_warnings"]:
            if "webdriver" in warning.lower():
                recommendations.append("CRITICAL: Hide navigator.webdriver using stealth injection")
            elif "plugins" in warning.lower():
                recommendations.append("CRITICAL: Add fake navigator.plugins to match real browser")
            elif "languages" in warning.lower():
                recommendations.append("CRITICAL: Set navigator.languages to match locale")
            elif "chrome_runtime" in warning.lower():
                recommendations.append("CRITICAL: Inject chrome.runtime object to avoid headless detection")
    
    if webgl.get("looks_suspicious"):
        recommendations.append("WARNING: WebGL vendor/renderer looks suspicious, consider randomizing")
    
    if headless.get("is_likely_headless"):
        recommendations.append("WARNING: Multiple headless indicators detected, consider running in headed mode or improving stealth")
    
    if benchmark["percentage"] < 80:
        recommendations.append("INFO: Stealth score below 80%, review all warnings before production use")
    
    if not recommendations:
        recommendations.append("✓ All critical checks passed. Ready for production use.")
    
    return recommendations
