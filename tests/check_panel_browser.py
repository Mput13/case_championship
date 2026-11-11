"""Проверка готового HTML в Chrome без сервера."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/verification"
OUT.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe", headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto((ROOT / "outputs/redwings_panel.html").as_uri(), wait_until="networkidle")
    ai = page.locator("#rw-ai-paper")
    ai.scroll_into_view_if_needed()
    page.evaluate("document.fonts.ready")
    assert page.evaluate('document.fonts.check(\'500 16px "Onest"\')')
    assert page.evaluate('document.fonts.check(\'500 16px "Montserrat Alternates"\')')
    assert ai.locator(".ap-current").count() == 9
    motion = ai.get_by_role("button")
    motion.click()
    assert motion.get_attribute("aria-pressed") == "false"
    motion.click()
    assert motion.get_attribute("aria-pressed") == "true"
    for width in (1440, 390, 320):
        page.set_viewport_size({"width": width, "height": 900})
        ai.scroll_into_view_if_needed()
        page.wait_for_timeout(150)
        assert ai.evaluate("el=>el.scrollWidth<=el.clientWidth")
        ai.screenshot(path=str(OUT / f"ai_workflow_{width}.png"))
    page.emulate_media(reduced_motion="reduce")
    motion.wait_for(state="hidden")
    page.emulate_media(reduced_motion="no-preference")
    page.set_viewport_size({"width": 1440, "height": 1100})
    assert page.locator("#ld .ld-row").count() >= 5
    for scenario in ("base", "cautious"):
        for support in (False, True):
            page.evaluate("([s,u]) => { SCEN=s; SUB=u; vsBoard(); netUpdate(); }", [scenario, support])
            assert page.locator("#ldk").is_disabled() == support
            for city in page.evaluate("D.cities.map(c=>c.iata)"):
                page.evaluate("city => { SEL=city; update(); }", city)
                state = page.evaluate("""() => ({
                    count: document.querySelectorAll('#mt tbody tr').length,
                    expected: NS_.routes.filter(r=>r.scenario===scenKey()&&r.vkey===NETV).length,
                    text: document.getElementById('ld').textContent,
                    label: document.getElementById('sc-sub').textContent
                })""")
                assert state["count"] == state["expected"] > 0, (scenario, support, city, state)
                assert "NaN" not in state["text"] and "undefined" not in state["text"]
            page.evaluate("() => { NETV='DIRECT'; vsBoard(); netUpdate(); }")
            assert page.locator("#mt tbody tr").count() >= 24
    page.evaluate("() => { SCEN='base'; SUB=true; SEL='OMS'; update(); vsBoard(); netUpdate(); }")
    page.locator("#vs").screenshot(path=str(OUT / "panel_base.png"))
    page.evaluate("() => { SCEN='cautious'; vsBoard(); netUpdate(); }")
    page.locator("#vs details").filter(has_text="Почему сценарии так различаются").evaluate("el=>el.open=true")
    page.locator("#vs").screenshot(path=str(OUT / "panel_cautious.png"))
    page.set_viewport_size({"width": 390, "height": 900})
    page.locator("#vs").screenshot(path=str(OUT / "panel_mobile.png"))
    assert not errors, errors
    result = {"passed": True, "city_scenario_combinations": 80, "direct_scenarios": 4,
              "javascript_errors": errors, "maps_loaded": page.evaluate("Boolean(window.d3)")}
    (OUT / "browser_checks.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result))
    browser.close()
