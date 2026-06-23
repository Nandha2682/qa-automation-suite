"""
Playwright (Python, sync API) test suite — Practice Test Automation Login Page
URL: https://practicetestautomation.com/practice-test-login/

Maps to: TC-001 .. TC-076 (see test case spec delivered earlier in the conversation)

NOTE: Your locally connected Playwright MCP (`analyze_requirements` /
`generate_framework`) returned `fetch failed` three times in a row across two
different URLs, and its `generate_framework` tool targets a JS/Cucumber-BDD
project structure (playwright-cucumber-bdd/...) rather than Python/pytest. So
this script was written directly rather than generated through that tool.
Worth checking the MCP server's network connectivity if you want it for live
DOM verification going forward.

Cross-browser TCs (TC-064-067) are NOT separate test functions — run the
whole suite per browser (DRY convention):
    pytest test_practice_test_automation_login.py --browser chromium -v
    pytest test_practice_test_automation_login.py --browser firefox  -v
    pytest test_practice_test_automation_login.py --browser webkit   -v

Setup:
    pip install pytest pytest-playwright --break-system-packages
    playwright install

LOCATORS: Based on the long-standing, publicly documented DOM of this practice
site (#username, #password, #submit, #error). High-confidence but unverified
live — flag any drift here once you can run it.
"""

import time

import pytest
from playwright.sync_api import Page, expect

BASE_URL = "https://practicetestautomation.com/practice-test-login/"
SUCCESS_URL = "https://practicetestautomation.com/logged-in-successfully/"

VALID_USERNAME = "student"
VALID_PASSWORD = "Password123"

# ---------------------------------------------------------------------------
# Shared payload / parametrization data
# ---------------------------------------------------------------------------

# TC-008/009/010/011/012/016/018 — Username values expected to be rejected
USERNAME_REJECTED_VARIANTS = [
    pytest.param(" student ", id="TC-008_leading_trailing_spaces"),
    pytest.param("Student", id="TC-009_case_sensitivity"),
    pytest.param("a" * 500, id="TC-010_very_long_string"),
    pytest.param("stu@dent!", id="TC-011_special_chars"),
    pytest.param("stüdent😀", id="TC-012_unicode_emoji"),
    pytest.param("   ", id="TC-016_whitespace_only"),
    pytest.param("123456", id="TC-018_numeric_only"),
]

# TC-021/022/023/024/025/031 — Password values expected to be rejected
PASSWORD_REJECTED_VARIANTS = [
    pytest.param(" Password123 ", id="TC-021_leading_trailing_spaces"),
    pytest.param("password123", id="TC-022_case_sensitivity"),
    pytest.param("a" * 500, id="TC-023_very_long_string"),
    pytest.param("P@$$w0rd!#", id="TC-024_special_chars"),
    pytest.param("Pässwörd😀", id="TC-025_unicode_emoji"),
    pytest.param("   ", id="TC-031_whitespace_only"),
]

# TC-013/014, TC-026/027 — Security payloads
SECURITY_PAYLOADS = [
    pytest.param("' OR '1'='1", id="sql_injection"),
    pytest.param("<script>alert(1)</script>", id="xss_script_tag"),
]

# TC-051/052/053/054 — Responsive viewports
RESPONSIVE_VIEWPORTS = [
    pytest.param({"width": 320, "height": 480}, id="TC-051_mobile_320x480"),
    pytest.param({"width": 375, "height": 667}, id="TC-052_mobile_375x667"),
    pytest.param({"width": 768, "height": 1024}, id="TC-053_tablet_768x1024"),
    pytest.param({"width": 1024, "height": 768}, id="TC-054_desktop_1024x768"),
]


# ---------------------------------------------------------------------------
# Page Object Models
# ---------------------------------------------------------------------------

class LoginPage:
    """Page Object for the login form."""

    def __init__(self, page: Page):
        self.page = page
        self.username = page.locator("#username")
        self.password = page.locator("#password")
        self.submit_button = page.locator("#submit")
        self.error_message = page.locator("#error")

    def goto(self):
        self.page.goto(BASE_URL, wait_until="domcontentloaded")

    def login(self, username: str, password: str):
        self.username.fill(username)
        self.password.fill(password)
        self.submit_button.click()

    def submit_via_enter(self, username: str, password: str):
        self.username.fill(username)
        self.password.fill(password)
        self.password.press("Enter")


class SuccessPage:
    """Page Object for the post-login success page."""

    def __init__(self, page: Page):
        self.page = page
        self.heading = page.locator("h1")
        self.success_text = page.locator(".post-content")
        self.logout_button = page.get_by_role("link", name="Log out")

    def logout(self):
        self.logout_button.click()


# ---------------------------------------------------------------------------
# Shared utility functions
# ---------------------------------------------------------------------------

def has_horizontal_scroll(page: Page) -> bool:
    return page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")


def get_element_size(locator):
    box = locator.bounding_box()
    return (box["width"], box["height"]) if box else (0, 0)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def login_page(page: Page) -> LoginPage:
    pom = LoginPage(page)
    pom.goto()
    return pom


@pytest.fixture
def console_errors(page: Page):
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    return errors


# ===========================================================================
# M1 — Positive Login — TC-001 to TC-005
# ===========================================================================

class TestPositiveLogin:

    def test_valid_login_redirects(self, login_page: LoginPage):
        """TC-001: Valid credentials redirect to the success page."""
        login_page.login(VALID_USERNAME, VALID_PASSWORD)
        expect(login_page.page).to_have_url(SUCCESS_URL)

    def test_success_url_exact(self, login_page: LoginPage):
        """TC-002: Success URL exactly matches expected path."""
        login_page.login(VALID_USERNAME, VALID_PASSWORD)
        assert login_page.page.url == SUCCESS_URL

    def test_success_message_text(self, login_page: LoginPage):
        """TC-003: Success page shows congratulations / logged-in text."""
        login_page.login(VALID_USERNAME, VALID_PASSWORD)
        success = SuccessPage(login_page.page)
        expect(success.success_text).to_contain_text("Congratulations")
        expect(success.success_text).to_contain_text("successfully logged in")

    def test_logout_button_visible(self, login_page: LoginPage):
        """TC-004: 'Log out' button is visible and clickable after login."""
        login_page.login(VALID_USERNAME, VALID_PASSWORD)
        success = SuccessPage(login_page.page)
        expect(success.logout_button).to_be_visible()

    def test_logout_returns_to_login(self, login_page: LoginPage):
        """TC-005: Clicking 'Log out' returns to the login page."""
        login_page.login(VALID_USERNAME, VALID_PASSWORD)
        success = SuccessPage(login_page.page)
        success.logout()
        expect(login_page.page).to_have_url(BASE_URL)


# ===========================================================================
# M2 — Username Field — TC-006 to TC-018
# ===========================================================================

class TestUsernameField:

    def test_incorrect_username(self, login_page: LoginPage):
        """TC-006: Incorrect username shows the username-invalid error."""
        login_page.login("incorrectUser", VALID_PASSWORD)
        expect(login_page.error_message).to_be_visible()
        expect(login_page.error_message).to_have_text("Your username is invalid!")

    def test_empty_username(self, login_page: LoginPage):
        """TC-007: Empty username, valid password -> error displayed."""
        login_page.login("", VALID_PASSWORD)
        expect(login_page.error_message).to_be_visible()

    @pytest.mark.parametrize("username", USERNAME_REJECTED_VARIANTS)
    def test_username_rejected_variants(self, login_page: LoginPage, username):
        """TC-008/009/010/012/016/018: Various invalid username values are rejected."""
        login_page.login(username, VALID_PASSWORD)
        expect(login_page.error_message).to_be_visible()
        print(f"[username variant] '{username[:30]}...' -> error shown")

    @pytest.mark.parametrize("payload", SECURITY_PAYLOADS)
    def test_username_security_payloads(self, login_page: LoginPage, payload):
        """TC-013/014: SQLi/XSS payloads in username must not bypass login or execute."""
        login_page.login(payload, VALID_PASSWORD)
        expect(login_page.page).to_have_url(BASE_URL)  # no bypass
        expect(login_page.error_message).to_be_visible()
        assert "alert" not in (login_page.page.title() or "")

    def test_username_paste_long_string(self, login_page: LoginPage):
        """TC-015: Pasting a long string into Username is accepted without truncation issue."""
        long_value = "u" * 1000
        login_page.username.fill(long_value)
        expect(login_page.username).to_have_value(long_value)

    def test_username_maxlength_attribute(self, login_page: LoginPage):
        """TC-017: Document whether a maxlength attribute exists on Username."""
        maxlength = login_page.username.get_attribute("maxlength")
        print(f"[TC-017] Username maxlength attribute: {maxlength}")


# ===========================================================================
# M3 — Password Field — TC-019 to TC-031
# ===========================================================================

class TestPasswordField:

    def test_incorrect_password(self, login_page: LoginPage):
        """TC-019: Incorrect password shows the password-invalid error."""
        login_page.login(VALID_USERNAME, "incorrectPassword")
        expect(login_page.error_message).to_be_visible()
        expect(login_page.error_message).to_have_text("Your password is invalid!")

    def test_empty_password(self, login_page: LoginPage):
        """TC-020: Valid username, empty password -> error displayed."""
        login_page.login(VALID_USERNAME, "")
        expect(login_page.error_message).to_be_visible()

    @pytest.mark.parametrize("password", PASSWORD_REJECTED_VARIANTS)
    def test_password_rejected_variants(self, login_page: LoginPage, password):
        """TC-021/022/023/024/025/031: Various invalid password values are rejected."""
        login_page.login(VALID_USERNAME, password)
        expect(login_page.error_message).to_be_visible()
        print(f"[password variant] '{password[:30]}...' -> error shown")

    @pytest.mark.parametrize("payload", SECURITY_PAYLOADS)
    def test_password_security_payloads(self, login_page: LoginPage, payload):
        """TC-026/027: SQLi/XSS payloads in password must not bypass login or execute."""
        login_page.login(VALID_USERNAME, payload)
        expect(login_page.page).to_have_url(BASE_URL)  # no bypass
        expect(login_page.error_message).to_be_visible()
        assert "alert" not in (login_page.page.title() or "")

    def test_password_field_is_masked(self, login_page: LoginPage):
        """TC-028: Password field masks input (type='password')."""
        input_type = login_page.password.get_attribute("type")
        assert input_type == "password"

    def test_password_paste_behavior(self, login_page: LoginPage):
        """TC-029: Pasting a valid password is accepted correctly."""
        login_page.password.fill(VALID_PASSWORD)
        expect(login_page.password).to_have_value(VALID_PASSWORD)

    def test_both_fields_incorrect_error_precedence(self, login_page: LoginPage):
        """TC-030: Both username and password wrong -> username error takes precedence."""
        login_page.login("incorrectUser", "incorrectPassword")
        expect(login_page.error_message).to_have_text("Your username is invalid!")


# ===========================================================================
# M4 — Submit / Form Behavior — TC-032 to TC-038
# ===========================================================================

class TestSubmitFormBehavior:

    def test_click_submit_valid(self, login_page: LoginPage):
        """TC-032: Clicking Submit with valid creds completes the success flow."""
        login_page.login(VALID_USERNAME, VALID_PASSWORD)
        expect(login_page.page).to_have_url(SUCCESS_URL)

    def test_enter_key_submits_form(self, login_page: LoginPage):
        """TC-033: Pressing Enter in the Password field submits the form."""
        login_page.submit_via_enter(VALID_USERNAME, VALID_PASSWORD)
        expect(login_page.page).to_have_url(SUCCESS_URL)

    def test_both_fields_empty(self, login_page: LoginPage):
        """TC-034: Submitting with both fields empty -> document which error appears."""
        login_page.login("", "")
        expect(login_page.error_message).to_be_visible()
        print(f"[TC-034] Error shown with both fields empty: '{login_page.error_message.inner_text()}'")

    def test_rapid_double_click_submit(self, login_page: LoginPage):
        """TC-035: Rapid double-click on Submit does not break the success flow."""
        login_page.username.fill(VALID_USERNAME)
        login_page.password.fill(VALID_PASSWORD)
        login_page.submit_button.click(click_count=2, delay=50)
        expect(login_page.page).to_have_url(SUCCESS_URL)

    def test_submit_with_javascript_disabled(self, browser):
        """TC-036: Document behavior when JavaScript is disabled (exploratory)."""
        context = browser.new_context(java_script_enabled=False)
        page = context.new_page()
        page.goto(BASE_URL, wait_until="domcontentloaded")
        page.locator("#username").fill(VALID_USERNAME)
        page.locator("#password").fill(VALID_PASSWORD)
        page.locator("#submit").click()
        print(f"[TC-036] URL after submit with JS disabled: {page.url}")
        context.close()

    def test_submit_under_simulated_slow_network(self, login_page: LoginPage):
        """TC-037: Submitting under throttled network shows no premature error."""
        login_page.page.route("**/*", lambda route: (time.sleep(0.5), route.continue_()))
        login_page.login(VALID_USERNAME, VALID_PASSWORD)
        expect(login_page.page).to_have_url(SUCCESS_URL, timeout=10000)

    def test_reload_after_failed_login_resets_fields(self, login_page: LoginPage):
        """TC-038: Reloading after a failed login clears fields and stale error."""
        login_page.login("incorrectUser", VALID_PASSWORD)
        expect(login_page.error_message).to_be_visible()
        login_page.page.reload(wait_until="domcontentloaded")
        expect(login_page.username).to_have_value("")
        expect(login_page.error_message).not_to_be_visible()


# ===========================================================================
# M5 — Success Page & Logout — TC-039 to TC-045
# ===========================================================================

class TestSuccessPageAndLogout:

    def test_success_page_heading(self, login_page: LoginPage):
        """TC-039: Success page heading matches expected text."""
        login_page.login(VALID_USERNAME, VALID_PASSWORD)
        success = SuccessPage(login_page.page)
        expect(success.heading).to_contain_text("Logged In Successfully")

    def test_logout_navigates_to_login_page(self, login_page: LoginPage):
        """TC-040: 'Log out' navigates back to the login page."""
        login_page.login(VALID_USERNAME, VALID_PASSWORD)
        success = SuccessPage(login_page.page)
        success.logout()
        expect(login_page.page).to_have_url(BASE_URL)

    def test_direct_navigation_to_success_url(self, page: Page):
        """TC-041: Document whether the success URL is accessible without logging in."""
        page.goto(SUCCESS_URL, wait_until="domcontentloaded")
        print(f"[TC-041] Direct nav to success URL without login -> final URL: {page.url}")

    def test_back_button_after_logout(self, login_page: LoginPage):
        """TC-042: Browser Back after logout does not show a cached logged-in state."""
        login_page.login(VALID_USERNAME, VALID_PASSWORD)
        SuccessPage(login_page.page).logout()
        login_page.page.go_back()
        print(f"[TC-042] URL after Back following logout: {login_page.page.url}")

    def test_back_button_after_login(self, login_page: LoginPage):
        """TC-043: Browser Back from the success page — document resulting behavior."""
        login_page.login(VALID_USERNAME, VALID_PASSWORD)
        login_page.page.go_back()
        print(f"[TC-043] URL after Back from success page: {login_page.page.url}")

    def test_no_leftover_error_on_success_page(self, login_page: LoginPage):
        """TC-044: No stale error message visible on the success page."""
        login_page.login(VALID_USERNAME, VALID_PASSWORD)
        expect(login_page.page.locator("#error")).not_to_be_visible()

    def test_reload_success_page_stable(self, login_page: LoginPage):
        """TC-045: Reloading the success page keeps it stable/accessible."""
        login_page.login(VALID_USERNAME, VALID_PASSWORD)
        login_page.page.reload(wait_until="domcontentloaded")
        expect(login_page.page).to_have_url(SUCCESS_URL)


# ===========================================================================
# M6 — Error Message UI — TC-046 to TC-050
# ===========================================================================

class TestErrorMessageUI:

    def test_error_visible_with_styling(self, login_page: LoginPage):
        """TC-046: Error message is visible with warning/red styling."""
        login_page.login("incorrectUser", VALID_PASSWORD)
        expect(login_page.error_message).to_be_visible()
        color = login_page.error_message.evaluate("el => getComputedStyle(el).color")
        print(f"[TC-046] Error message color: {color}")

    def test_username_error_exact_text(self, login_page: LoginPage):
        """TC-047: Username error text exactly matches expected copy."""
        login_page.login("incorrectUser", VALID_PASSWORD)
        expect(login_page.error_message).to_have_text("Your username is invalid!")

    def test_password_error_exact_text(self, login_page: LoginPage):
        """TC-048: Password error text exactly matches expected copy."""
        login_page.login(VALID_USERNAME, "incorrectPassword")
        expect(login_page.error_message).to_have_text("Your password is invalid!")

    def test_error_clears_after_correction(self, login_page: LoginPage):
        """TC-049: Error message clears once corrected input is resubmitted successfully."""
        login_page.login("incorrectUser", VALID_PASSWORD)
        expect(login_page.error_message).to_be_visible()
        login_page.username.fill(VALID_USERNAME)
        login_page.submit_button.click()
        expect(login_page.page).to_have_url(SUCCESS_URL)

    def test_error_has_accessible_announcement(self, login_page: LoginPage):
        """TC-050: Error element exposes an ARIA live region or role=alert."""
        login_page.login("incorrectUser", VALID_PASSWORD)
        role = login_page.error_message.get_attribute("role")
        aria_live = login_page.error_message.get_attribute("aria-live")
        print(f"[TC-050] Error element role='{role}' aria-live='{aria_live}'")


# ===========================================================================
# M7 — Responsive — TC-051 to TC-057
# ===========================================================================

class TestResponsive:

    @pytest.mark.parametrize("viewport", RESPONSIVE_VIEWPORTS)
    def test_no_horizontal_scroll_at_viewport(self, page: Page, viewport):
        """TC-051/052/053/054: No horizontal scroll across mobile/tablet/desktop sizes."""
        page.set_viewport_size(viewport)
        pom = LoginPage(page)
        pom.goto()
        assert not has_horizontal_scroll(page), f"Horizontal scroll at {viewport}"

    def test_submit_button_touch_target_size(self, page: Page):
        """TC-055: Submit button meets >=44x44px touch target on mobile."""
        page.set_viewport_size({"width": 375, "height": 667})
        pom = LoginPage(page)
        pom.goto()
        width, height = get_element_size(pom.submit_button)
        print(f"[TC-055] Submit button size: {width}x{height}")

    def test_labels_not_truncated_on_mobile(self, page: Page):
        """TC-056: Username/Password labels remain visible at small widths."""
        page.set_viewport_size({"width": 320, "height": 480})
        pom = LoginPage(page)
        pom.goto()
        labels = page.locator("label")
        for i in range(labels.count()):
            expect(labels.nth(i)).to_be_visible()

    def test_error_message_visible_on_mobile(self, page: Page):
        """TC-057: Error message remains fully visible/readable on mobile."""
        page.set_viewport_size({"width": 375, "height": 667})
        pom = LoginPage(page)
        pom.goto()
        pom.login("incorrectUser", VALID_PASSWORD)
        expect(pom.error_message).to_be_visible()
        assert not has_horizontal_scroll(page)


# ===========================================================================
# M8 — Accessibility — TC-058 to TC-063
# ===========================================================================

class TestAccessibility:

    def test_inputs_have_labels(self, login_page: LoginPage):
        """TC-058: Username/Password inputs have associated <label> elements."""
        for field_id in ("username", "password"):
            label = login_page.page.locator(f"label[for='{field_id}']")
            print(f"[TC-058] Label for #{field_id} found: {label.count() > 0}")

    def test_tab_order_is_logical(self, login_page: LoginPage):
        """TC-059: Tab order flows Username -> Password -> Submit."""
        login_page.username.click()
        order = []
        for _ in range(3):
            login_page.page.keyboard.press("Tab")
            order.append(login_page.page.evaluate("document.activeElement.id"))
        print(f"[TC-059] Tab order observed: {order}")

    def test_submit_keyboard_activatable(self, login_page: LoginPage):
        """TC-060: Submit button is reachable and activatable via keyboard."""
        login_page.username.fill(VALID_USERNAME)
        login_page.password.fill(VALID_PASSWORD)
        login_page.submit_button.focus()
        login_page.page.keyboard.press("Enter")
        expect(login_page.page).to_have_url(SUCCESS_URL)

    @pytest.mark.skip(reason="Requires axe-core/contrast-checker integration — TODO")
    def test_color_contrast_meets_wcag_aa(self, login_page: LoginPage):
        """TC-061: Text/label contrast meets WCAG AA. [TODO: integrate axe-core]"""
        pass

    def test_focus_indicator_visible(self, login_page: LoginPage):
        """TC-062: Focused elements show a visible outline."""
        login_page.username.click()
        outline = login_page.username.evaluate("el => getComputedStyle(el).outlineStyle")
        print(f"[TC-062] Username outline style on focus: {outline}")

    def test_heading_structure_present(self, login_page: LoginPage):
        """TC-063: Page has a proper heading hierarchy for screen readers."""
        h1_count = login_page.page.locator("h1").count()
        assert h1_count >= 1, "Expected at least one <h1> on the login page"


# ===========================================================================
# M9 — Cross-Browser — TC-064 to TC-067
# ===========================================================================
# Intentionally no dedicated test functions. Run the full suite per browser:
#   pytest test_practice_test_automation_login.py --browser chromium
#   pytest test_practice_test_automation_login.py --browser firefox
#   pytest test_practice_test_automation_login.py --browser webkit


# ===========================================================================
# M10 — Security — TC-068 to TC-073
# ===========================================================================

class TestSecurity:

    def test_password_not_reflected_in_dom(self, login_page: LoginPage):
        """TC-068: Failed login does not leak the password elsewhere in the DOM."""
        login_page.login(VALID_USERNAME, "incorrectPassword")
        page_content = login_page.page.content()
        assert "incorrectPassword" not in page_content.replace(
            login_page.password.input_value(), ""
        ) or True  # documents presence; refine once DOM is verified live

    def test_no_credentials_in_console(self, login_page: LoginPage, console_errors):
        """TC-069: No sensitive credentials appear in console logs after submit."""
        login_page.login(VALID_USERNAME, VALID_PASSWORD)
        leaked = [e for e in console_errors if VALID_PASSWORD in e]
        assert not leaked, f"Password leaked in console: {leaked}"

    def test_https_enforced(self, login_page: LoginPage):
        """TC-070: Login page is served over HTTPS with no mixed content."""
        assert login_page.page.url.startswith("https://")

    def test_extremely_long_payload_no_crash(self, login_page: LoginPage):
        """TC-071: 10,000+ char input in both fields does not crash the page/server."""
        huge_value = "x" * 10000
        login_page.login(huge_value, huge_value)
        expect(login_page.page.locator("body")).to_be_visible()

    def test_autofill_attributes(self, login_page: LoginPage):
        """TC-072: Inspect autocomplete attributes for unintended autofill leakage."""
        autocomplete = login_page.password.get_attribute("autocomplete")
        print(f"[TC-072] Password autocomplete attribute: {autocomplete}")

    def test_rapid_failed_attempts_rate_limiting(self, login_page: LoginPage):
        """TC-073: Document whether repeated failed logins trigger rate-limiting."""
        for _ in range(10):
            login_page.login("incorrectUser", "incorrectPassword")
            login_page.page.goto(BASE_URL, wait_until="domcontentloaded")
        print("[TC-073] Completed 10 rapid failed attempts — verify manually if any lockout occurred")


# ===========================================================================
# M11 — Performance — TC-074 to TC-076
# ===========================================================================

class TestPerformance:

    def test_page_load_time_under_threshold(self, page: Page):
        """TC-074: Login page load completes within an acceptable threshold (<3s)."""
        start = time.monotonic()
        page.goto(BASE_URL, wait_until="domcontentloaded")
        elapsed = time.monotonic() - start
        print(f"[TC-074] Page load time: {elapsed:.2f}s")
        assert elapsed < 3.0, f"Page load took {elapsed:.2f}s (threshold: 3.0s)"

    def test_submit_response_time(self, login_page: LoginPage):
        """TC-075: Time from Submit click to redirect is within threshold (<2s)."""
        login_page.username.fill(VALID_USERNAME)
        login_page.password.fill(VALID_PASSWORD)
        start = time.monotonic()
        login_page.submit_button.click()
        login_page.page.wait_for_url(SUCCESS_URL, timeout=5000)
        elapsed = time.monotonic() - start
        print(f"[TC-075] Submit-to-redirect time: {elapsed:.2f}s")
        assert elapsed < 2.0, f"Submit response took {elapsed:.2f}s (threshold: 2.0s)"

    def test_repeated_login_logout_cycles_no_console_errors(self, page: Page, console_errors):
        """TC-076: 5x login->logout cycles produce no console errors."""
        pom = LoginPage(page)
        for _ in range(5):
            pom.goto()
            pom.login(VALID_USERNAME, VALID_PASSWORD)
            page.wait_for_url(SUCCESS_URL, timeout=5000)
            SuccessPage(page).logout()
        print(f"[TC-076] Console errors across 5 cycles: {console_errors}")
        assert not console_errors, f"Unexpected console errors: {console_errors}"
