"""Mock HTML pages for testing survey flows."""

MOCK_SURVEY_HTML = """
<!DOCTYPE html>
<html><head><title>Test Survey</title></head><body>
  <div id="consent"><button id="accept-all">Alle akzeptieren</button></div>
  <form id="survey">
    <h2>Frage 1: Wie zufrieden sind Sie?</h2>
    <label><input type="radio" name="q1" value="high"> Sehr zufrieden</label>
    <label><input type="radio" name="q1" value="mid"> Neutral</label>
    <label><input type="radio" name="q1" value="low"> Unzufrieden</label>
    <button type="button" id="next-step">Weiter zur nächsten Frage</button>
  </form>
  <script>
    document.getElementById('next-step').addEventListener('click', () => {
      document.getElementById('survey').innerHTML = '<h2>Vielen Dank für Ihre Teilnahme!</h2>';
    });
  </script>
</body></html>
"""

MOCK_DYNAMIC_HTML = """
<!DOCTYPE html>
<html><head><title>Dynamic Content Test</title></head><body>
  <div id="loader">Lade Umfrage...</div>
  <script>
    setTimeout(() => {
      document.getElementById('loader').remove();
      document.body.innerHTML += '<button class="submit-btn" aria-label="Absenden">Absenden</button>';
    }, 800);
  </script>
</body></html>
"""

MOCK_CONSENT_HTML = """
<!DOCTYPE html>
<html><head><title>Consent Banner Test</title></head><body>
  <div id="cookie-banner" role="dialog" aria-label="Cookie Consent">
    <p>Diese Website verwendet Cookies.</p>
    <button id="accept-cookies" data-testid="accept-all">Alle akzeptieren</button>
    <button id="reject-cookies">Nur notwendige</button>
  </div>
  <div id="main-content" style="display:none;">
    <h1>Willkommen zur Umfrage</h1>
    <button id="start-survey">Jetzt starten</button>
  </div>
  <script>
    document.getElementById('accept-cookies').addEventListener('click', () => {
      document.getElementById('cookie-banner').style.display = 'none';
      document.getElementById('main-content').style.display = 'block';
    });
  </script>
</body></html>
"""

MOCK_MULTI_STEP_HTML = """
<!DOCTYPE html>
<html><head><title>Multi-Step Survey</title></head><body>
  <div id="step-1">
    <h2>Schritt 1: Persönliche Daten</h2>
    <label>Name: <input type="text" id="name" placeholder="Ihr Name"></label>
    <button id="step-1-next">Weiter zu Schritt 2</button>
  </div>
  <div id="step-2" style="display:none;">
    <h2>Schritt 2: Bewertung</h2>
    <label>Bewertung: <input type="range" id="rating" min="1" max="10"></label>
    <button id="step-2-submit">Absenden</button>
  </div>
  <div id="thank-you" style="display:none;">
    <h2>Vielen Dank!</h2>
  </div>
  <script>
    document.getElementById('step-1-next').addEventListener('click', () => {
      document.getElementById('step-1').style.display = 'none';
      document.getElementById('step-2').style.display = 'block';
    });
    document.getElementById('step-2-submit').addEventListener('click', () => {
      document.getElementById('step-2').style.display = 'none';
      document.getElementById('thank-you').style.display = 'block';
    });
  </script>
</body></html>
"""
