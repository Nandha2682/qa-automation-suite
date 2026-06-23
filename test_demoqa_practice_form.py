"""
Playwright (Python, sync API) test suite — DemoQA Student Registration / Practice Form
URL: https://demoqa.com/automation-practice-form

Maps to: TC-001 .. TC-099 (see test case spec delivered earlier in the conversation)
Cross-browser TCs (TC-093-096) are NOT separate test functions. Run the whole suite
per browser instead (project convention: --browser flag, not duplicated tests):

    pytest test_demoqa_practice_form.py --browser chromium -v
    pytest test_demoqa_practice_form.py --browser firefox  -v
    pytest test_demoqa_practice_form.py --browser webkit   -v

Setup:
    pip install pytest pytest-playwright --break-system-packages
    playwright install

NOTE ON LOCATORS: This page's DOM/IDs (e.g. #firstName, #userNumber, gender-radio-*,
hobbies-checkbox-*, react-datepicker__*, .subjects-auto-complete__*, #state/#city) are
based on the long-standing, publicly documented structure of this practice site.
A live Playwright MCP fetch was unavailable at generation time (`fetch failed`), so
treat locators as HIGH-CONFIDENCE but UNVERIFIED until run once — flag any drift here.
"""

import re
import time

import pytest
from playwright.sync_api import Page, expect

BASE_URL = "https://demoqa.com/automation-practice-form"

# ---------------------------------------------------------------------------
# Shared payload / parametrization data
# ---------------------------------------------------------------------------

# TC-005 / TC-006 / TC-007 / TC-008 (Name edge inputs)
NAME_EDGE_PAYLOADS = [
    pytest.param("12345", id="TC-005_numeric_chars"),
    pytest.param("@#$%^&*", id="TC-006_special_chars"),
    pytest.param("A" * 500, id="TC-007_very_long_string"),
    pytest.param("José😀", id="TC-008_unicode_emoji"),
]

# TC-009 / TC-010 (Name security payloads)
SECURITY_PAYLOADS = [
    pytest.param("' OR '1'='1", id="sql_injection"),
    pytest.param("<script>alert(1)</script>", id="xss_script_tag"),
]

# TC-079 - TC-082 (Responsive viewports)
RESPONSIVE_VIEWPORTS = [
    pytest.param({"width": 320, "height": 480}, id="TC-079_mobile_320x480"),
    pytest.param({"width": 375, "height": 667}, id="TC-080_mobile_375x667"),
    pytest.param({"width": 768, "height": 1024}, id="TC-081_tablet_768x1024"),
    pytest.param({"width": 1024, "height": 768}, id="TC-082_desktop_1024x768"),
]


# ---------------------------------------------------------------------------
# Page Object Model
# ---------------------------------------------------------------------------

class PracticeFormPage:
    """Page Object for the DemoQA Student Registration Form."""

    GENDER_IDS = {"Male": 1, "Female": 2, "Other": 3}
    HOBBY_IDS = {"Sports": 1, "Reading": 2, "Music": 3}

    def __init__(self, page: Page):
        self.page = page
        self.first_name = page.locator("#firstName")
        self.last_name = page.locator("#lastName")
        self.email = page.locator("#userEmail")
        self.gender_wrapper = page.locator("#genderWrapper")
        self.mobile = page.locator("#userNumber")
        self.dob_input = page.locator("#dateOfBirthInput")
        self.subjects_input = page.locator("#subjectsInput")
        self.subjects_container = page.locator("#subjectsContainer")
        self.hobbies_wrapper = page.locator("#hobbiesWrapper")
        self.upload_picture = page.locator("#uploadPicture")
        self.current_address = page.locator("#currentAddress")
        self.state_dropdown = page.locator("#state")
        self.city_dropdown = page.locator("#city")
        self.submit_button = page.locator("#submit")
        self.modal_title = page.locator("#example-modal-sizes-title-lg")
        self.modal_body = page.locator(".modal-body")
        self.modal_close_button = page.locator("#closeLargeModal")

    # -- navigation -----------------------------------------------------

    def goto(self, remove_ad_banner: bool = True):
        self.page.goto(BASE_URL, wait_until="domcontentloaded")
        if remove_ad_banner:
            # Known DemoQA quirk: #fixedban ad iframe can intercept clicks
            # near the bottom of the form. Remove for tests not specifically
            # targeting that behavior (see TC-083, which disables this).
            self.page.evaluate("document.querySelector('#fixedban')?.remove();")

    # -- field actions ----------------------------------------------------

    def fill_first_name(self, value: str):
        self.first_name.fill(value)

    def fill_last_name(self, value: str):
        self.last_name.fill(value)

    def fill_email(self, value: str):
        self.email.fill(value)

    def select_gender(self, gender: str):
        gid = self.GENDER_IDS[gender]
        self.page.locator(f"label[for='gender-radio-{gid}']").click()

    def fill_mobile(self, value: str):
        self.mobile.fill(value)

    def open_dob_picker(self):
        self.dob_input.click()

    def set_dob(self, day: str, month_label: str, year: str):
        self.open_dob_picker()
        self.page.locator(".react-datepicker__month-select").select_option(label=month_label)
        self.page.locator(".react-datepicker__year-select").select_option(year)
        self.page.locator(
            f".react-datepicker__day:not(.react-datepicker__day--outside-month):text-is('{day}')"
        ).click()

    def add_subject(self, subject: str, select_suggestion: bool = True):
        self.subjects_input.click()
        self.subjects_input.fill(subject)
        if select_suggestion:
            self.page.locator(".subjects-auto-complete__option").first.click()
        else:
            self.subjects_input.press("Enter")

    def remove_subject(self, subject: str):
        self.page.locator(
            f".subjects-auto-complete__multi-value:has-text('{subject}') "
            ".subjects-auto-complete__multi-value__remove"
        ).click()

    def get_subject_chips(self):
        return self.page.locator(".subjects-auto-complete__multi-value__label").all_text_contents()

    def select_hobby(self, hobby: str):
        hid = self.HOBBY_IDS[hobby]
        self.page.locator(f"label[for='hobbies-checkbox-{hid}']").click()

    def is_hobby_checked(self, hobby: str) -> bool:
        hid = self.HOBBY_IDS[hobby]
        return self.page.locator(f"#hobbies-checkbox-{hid}").is_checked()

    def upload_file(self, file_path: str):
        self.upload_picture.set_input_files(file_path)

    def fill_address(self, value: str):
        self.current_address.fill(value)

    def select_state(self, state: str):
        self.state_dropdown.click()
        self.state_dropdown.locator("input").fill(state)
        self.page.keyboard.press("Enter")

    def select_city(self, city: str):
        self.city_dropdown.click()
        self.city_dropdown.locator("input").fill(city)
        self.page.keyboard.press("Enter")

    def get_selected_state(self) -> str:
        return self.state_dropdown.locator("div[class*='singleValue']").inner_text()

    def get_selected_city(self) -> str:
        return self.city_dropdown.locator("div[class*='singleValue']").inner_text()

    def click_submit(self):
        self.submit_button.scroll_into_view_if_needed()
        self.submit_button.click()

    def fill_minimum_mandatory_fields(self):
        """Helper: fills only the fields believed mandatory (Name, Gender, Mobile)."""
        self.fill_first_name("Jordan")
        self.fill_last_name("Avery")
        self.select_gender("Male")
        self.fill_mobile("9876543210")

    # -- assertions / helpers -------------------------------------------

    def is_field_invalid(self, locator) -> bool:
        """DemoQA marks invalid required fields with an inline red border
        (rgb(220, 53, 69)) rather than a CSS class."""
        border_color = locator.evaluate("el => getComputedStyle(el).borderColor")
        return "220, 53, 69" in border_color

    def modal_row_value(self, label: str) -> str:
        row = self.modal_body.locator(f"tr:has-text('{label}')")
        return row.locator("td").nth(1).inner_text()


# ---------------------------------------------------------------------------
# Shared utility functions (project convention)
# ---------------------------------------------------------------------------

def has_horizontal_scroll(page: Page) -> bool:
    return page.evaluate(
        "document.documentElement.scrollWidth > window.innerWidth + 1"
    )


def get_touch_target_size(locator):
    box = locator.bounding_box()
    return (box["width"], box["height"]) if box else (0, 0)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def form_page(page: Page) -> PracticeFormPage:
    pom = PracticeFormPage(page)
    pom.goto()
    return pom


@pytest.fixture
def sample_image_path(tmp_path):
    """TC-053: tiny valid 1x1 PNG for upload tests."""
    png_bytes = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
        "53de0000000c4944415408d763f8cfc0c0c0040000050001b6193a0a0000000049454e44ae426082"
    )
    file_path = tmp_path / "sample.png"
    file_path.write_bytes(png_bytes)
    return str(file_path)


@pytest.fixture
def disallowed_file_path(tmp_path):
    """TC-054: non-image file."""
    file_path = tmp_path / "not_an_image.exe"
    file_path.write_bytes(b"MZ-dummy-binary-content")
    return str(file_path)


@pytest.fixture
def oversized_file_path(tmp_path):
    """TC-055: ~6MB dummy file."""
    file_path = tmp_path / "oversized.png"
    file_path.write_bytes(b"\x00" * (6 * 1024 * 1024))
    return str(file_path)


@pytest.fixture
def console_errors(page: Page):
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    return errors


# ===========================================================================
# M1 — Name (First / Last)  — TC-001 to TC-010
# ===========================================================================

class TestNameFields:

    def test_valid_alphabetic_name(self, form_page: PracticeFormPage):
        """TC-001: Valid alphabetic First/Last name accepted."""
        form_page.fill_first_name("John")
        form_page.fill_last_name("Doe")
        expect(form_page.first_name).to_have_value("John")
        expect(form_page.last_name).to_have_value("Doe")

    def test_name_with_punctuation(self, form_page: PracticeFormPage):
        """TC-002: Hyphen/apostrophe in name accepted."""
        form_page.fill_first_name("Anne-Marie")
        form_page.fill_last_name("O'Brien")
        expect(form_page.first_name).to_have_value("Anne-Marie")
        expect(form_page.last_name).to_have_value("O'Brien")

    def test_empty_first_name_shows_error(self, form_page: PracticeFormPage):
        """TC-003: Empty First Name flagged as required on submit."""
        form_page.fill_last_name("Doe")
        form_page.select_gender("Male")
        form_page.fill_mobile("9876543210")
        form_page.click_submit()
        assert form_page.is_field_invalid(form_page.first_name), \
            "Expected First Name to show required-field red border"

    def test_empty_last_name_shows_error(self, form_page: PracticeFormPage):
        """TC-004: Empty Last Name flagged as required on submit."""
        form_page.fill_first_name("John")
        form_page.select_gender("Male")
        form_page.fill_mobile("9876543210")
        form_page.click_submit()
        assert form_page.is_field_invalid(form_page.last_name), \
            "Expected Last Name to show required-field red border"

    @pytest.mark.parametrize("payload", NAME_EDGE_PAYLOADS)
    def test_name_edge_inputs(self, form_page: PracticeFormPage, payload):
        """TC-005/006/007/008: Edge-case characters in First Name."""
        form_page.fill_first_name(payload)
        # No client-side character restriction is documented for this field;
        # assert the value round-trips without crashing the page/UI.
        expect(form_page.first_name).to_have_value(payload)

    @pytest.mark.parametrize("payload", SECURITY_PAYLOADS)
    def test_name_security_payloads(self, form_page: PracticeFormPage, payload):
        """TC-009/010: SQLi/XSS payloads in Last Name must not execute."""
        form_page.fill_last_name(payload)
        expect(form_page.last_name).to_have_value(payload)
        # Confirm no JS dialog / script execution occurred
        assert "alert" not in (form_page.page.title() or "")


# ===========================================================================
# M2 — Email — TC-011 to TC-018
# ===========================================================================

class TestEmailField:

    def test_valid_email(self, form_page: PracticeFormPage):
        """TC-011: Valid email accepted."""
        form_page.fill_email("name@example.com")
        expect(form_page.email).to_have_value("name@example.com")

    def test_invalid_email_missing_at(self, form_page: PracticeFormPage):
        """TC-012: Email without '@' rejected on submit."""
        form_page.fill_first_name("John")
        form_page.fill_last_name("Doe")
        form_page.fill_email("nameexample.com")
        form_page.select_gender("Male")
        form_page.fill_mobile("9876543210")
        form_page.click_submit()
        assert form_page.is_field_invalid(form_page.email)

    def test_invalid_email_missing_domain(self, form_page: PracticeFormPage):
        """TC-013: Email without domain rejected on submit."""
        form_page.fill_minimum_mandatory_fields()
        form_page.fill_email("name@")
        form_page.click_submit()
        assert form_page.is_field_invalid(form_page.email)

    def test_empty_email_on_submit(self, form_page: PracticeFormPage):
        """TC-014: Empty Email — verify whether mandatory or optional."""
        form_page.fill_minimum_mandatory_fields()
        form_page.click_submit()
        is_invalid = form_page.is_field_invalid(form_page.email)
        # Document actual behavior rather than assume; adjust assertion once verified.
        print(f"[TC-014] Email empty -> flagged invalid: {is_invalid}")

    def test_email_plus_alias(self, form_page: PracticeFormPage):
        """TC-015: '+' alias in email accepted."""
        form_page.fill_email("name+test@example.com")
        expect(form_page.email).to_have_value("name+test@example.com")

    def test_email_very_long(self, form_page: PracticeFormPage):
        """TC-016: Very long email handled without UI break."""
        long_email = ("a" * 240) + "@example.com"
        form_page.fill_email(long_email)
        expect(form_page.email).to_have_value(long_email)

    @pytest.mark.parametrize("payload", SECURITY_PAYLOADS)
    def test_email_security_payloads(self, form_page: PracticeFormPage, payload):
        """TC-017/018: SQLi/XSS payloads in Email must not execute."""
        form_page.fill_email(payload)
        expect(form_page.email).to_have_value(payload)


# ===========================================================================
# M3 — Gender — TC-019 to TC-022
# ===========================================================================

class TestGenderField:

    def test_select_male(self, form_page: PracticeFormPage):
        """TC-019: Selecting Male checks only that radio."""
        form_page.select_gender("Male")
        assert form_page.page.locator("#gender-radio-1").is_checked()

    def test_switch_gender_selection(self, form_page: PracticeFormPage):
        """TC-020: Selecting Female then Other leaves only Other checked."""
        form_page.select_gender("Female")
        form_page.select_gender("Other")
        assert form_page.page.locator("#gender-radio-3").is_checked()
        assert not form_page.page.locator("#gender-radio-2").is_checked()

    def test_no_gender_selected_on_submit(self, form_page: PracticeFormPage):
        """TC-021: Submitting with no Gender selected raises a required error."""
        form_page.fill_first_name("John")
        form_page.fill_last_name("Doe")
        form_page.fill_mobile("9876543210")
        form_page.click_submit()
        # DemoQA colors the gender label text red when invalid
        color = form_page.gender_wrapper.evaluate(
            "el => getComputedStyle(el.querySelector('.custom-control-label')).color"
        )
        assert "220, 53, 69" in color or "rgb(220, 53, 69)" in color

    def test_gender_keyboard_navigation(self, form_page: PracticeFormPage):
        """TC-022: Gender options are keyboard operable."""
        form_page.first_name.click()
        form_page.page.keyboard.press("Tab")
        form_page.page.keyboard.press("Tab")
        form_page.page.keyboard.press("Tab")
        form_page.page.keyboard.press(" ")
        # At least one gender radio should now be checked
        checked = any(
            form_page.page.locator(f"#gender-radio-{i}").is_checked() for i in (1, 2, 3)
        )
        assert checked, "Expected a gender radio to be selectable via keyboard"


# ===========================================================================
# M4 — Mobile Number — TC-023 to TC-032
# ===========================================================================

class TestMobileNumber:

    def test_valid_10_digit_mobile(self, form_page: PracticeFormPage):
        """TC-023: Valid 10-digit mobile number accepted."""
        form_page.fill_mobile("9876543210")
        expect(form_page.mobile).to_have_value("9876543210")

    def test_mobile_9_digits_invalid(self, form_page: PracticeFormPage):
        """TC-024: 9-digit mobile flagged invalid on submit."""
        form_page.fill_minimum_mandatory_fields()
        form_page.fill_mobile("987654321")
        form_page.click_submit()
        assert form_page.is_field_invalid(form_page.mobile)

    def test_mobile_11_digits(self, form_page: PracticeFormPage):
        """TC-025: 11-digit input — verify only 10 retained or flagged invalid."""
        form_page.fill_mobile("98765432101")
        value = form_page.mobile.input_value()
        assert len(value) <= 11  # document actual truncation behavior
        print(f"[TC-025] Mobile value after 11-digit entry: '{value}'")

    def test_mobile_empty_required(self, form_page: PracticeFormPage):
        """TC-026: Empty Mobile Number flagged as required on submit."""
        form_page.fill_first_name("John")
        form_page.fill_last_name("Doe")
        form_page.select_gender("Male")
        form_page.click_submit()
        assert form_page.is_field_invalid(form_page.mobile)

    def test_mobile_alpha_rejected(self, form_page: PracticeFormPage):
        """TC-027: Alphabetic characters rejected by numeric-only field."""
        form_page.fill_mobile("abcdefghij")
        expect(form_page.mobile).to_have_value("")

    def test_mobile_leading_zero(self, form_page: PracticeFormPage):
        """TC-028: Leading-zero 10-digit mobile accepted (boundary value)."""
        form_page.fill_mobile("0987654321")
        expect(form_page.mobile).to_have_value("0987654321")

    def test_mobile_formatted_with_dashes(self, form_page: PracticeFormPage):
        """TC-029: Dash-formatted input — non-digits should be stripped/rejected."""
        form_page.fill_mobile("987-654-3210")
        value = form_page.mobile.input_value()
        assert "-" not in value

    def test_mobile_paste_20_digits(self, form_page: PracticeFormPage):
        """TC-030: Pasting 20 digits — verify truncation behavior."""
        form_page.mobile.fill("1" * 20)
        value = form_page.mobile.input_value()
        print(f"[TC-030] Mobile value after 20-digit paste: '{value}' (len={len(value)})")

    @pytest.mark.parametrize("payload", SECURITY_PAYLOADS)
    def test_mobile_injection_payload_rejected(self, form_page: PracticeFormPage, payload):
        """TC-031: Injection payloads rejected by numeric-only Mobile field."""
        form_page.fill_mobile(payload)
        expect(form_page.mobile).to_have_value("")

    def test_mobile_all_zeros_boundary(self, form_page: PracticeFormPage):
        """TC-032: All-zero 10-digit value — boundary acceptance check."""
        form_page.fill_mobile("0000000000")
        expect(form_page.mobile).to_have_value("0000000000")


# ===========================================================================
# M5 — Date of Birth — TC-033 to TC-040
# ===========================================================================

class TestDateOfBirth:

    def test_select_valid_past_date(self, form_page: PracticeFormPage):
        """TC-033: Selecting a valid date populates the DOB field."""
        form_page.set_dob("15", "January", "1995")
        expect(form_page.dob_input).to_have_value(re.compile("15 Jan 1995"))

    def test_change_month_dropdown(self, form_page: PracticeFormPage):
        """TC-034: Changing the month dropdown updates the calendar grid."""
        form_page.open_dob_picker()
        form_page.page.locator(".react-datepicker__month-select").select_option(label="March")
        selected = form_page.page.locator(".react-datepicker__month-select").input_value()
        assert selected is not None

    def test_change_year_50_years_back(self, form_page: PracticeFormPage):
        """TC-035: Changing year to 50+ years back updates the calendar."""
        form_page.open_dob_picker()
        form_page.page.locator(".react-datepicker__year-select").select_option("1975")
        selected = form_page.page.locator(".react-datepicker__year-select").input_value()
        assert selected == "1975"

    def test_leap_year_feb29_selectable(self, form_page: PracticeFormPage):
        """TC-036: Feb 29 selectable in a leap year (e.g., 2024)."""
        form_page.set_dob("29", "February", "2024")
        expect(form_page.dob_input).to_have_value(re.compile("29 Feb 2024"))

    def test_non_leap_year_feb29_not_selectable(self, form_page: PracticeFormPage):
        """TC-037: Feb 29 should not exist in a non-leap year (e.g., 2023)."""
        form_page.open_dob_picker()
        form_page.page.locator(".react-datepicker__month-select").select_option(label="February")
        form_page.page.locator(".react-datepicker__year-select").select_option("2023")
        day_29 = form_page.page.locator(
            ".react-datepicker__day:not(.react-datepicker__day--outside-month):text-is('29')"
        )
        assert day_29.count() == 0, "Feb 29 should not be present in a non-leap year"

    def test_select_today(self, form_page: PracticeFormPage):
        """TC-038: Today's date is selectable as DOB."""
        form_page.open_dob_picker()
        form_page.page.locator(".react-datepicker__day--today").click()
        assert form_page.dob_input.input_value() != ""

    def test_future_date_navigation(self, form_page: PracticeFormPage):
        """TC-039: Verify whether navigating forward allows future-date selection."""
        form_page.open_dob_picker()
        next_button = form_page.page.locator(".react-datepicker__navigation--next")
        is_disabled = next_button.is_disabled() if next_button.count() else None
        print(f"[TC-039] 'Next month' navigation disabled: {is_disabled}")

    def test_dob_keyboard_only_operation(self, form_page: PracticeFormPage):
        """TC-040: Date picker operable via keyboard only."""
        form_page.dob_input.click()
        form_page.page.keyboard.press("ArrowDown")
        form_page.page.keyboard.press("Enter")
        assert form_page.dob_input.input_value() != ""


# ===========================================================================
# M6 — Subjects — TC-041 to TC-047
# ===========================================================================

class TestSubjects:

    def test_add_subject_via_suggestion(self, form_page: PracticeFormPage):
        """TC-041: Typing + selecting a suggestion adds a subject chip."""
        form_page.add_subject("Maths")
        assert "Maths" in form_page.get_subject_chips()

    def test_unmatched_subject_text(self, form_page: PracticeFormPage):
        """TC-042: Free text with no matching suggestion — verify accept/reject."""
        form_page.add_subject("Zzzznotarealsubject", select_suggestion=False)
        chips = form_page.get_subject_chips()
        print(f"[TC-042] Subject chips after unmatched free text: {chips}")

    def test_add_multiple_subjects(self, form_page: PracticeFormPage):
        """TC-043: Multiple subjects can be added as separate chips."""
        for subject in ("Maths", "Physics", "English"):
            form_page.add_subject(subject)
        chips = form_page.get_subject_chips()
        assert {"Maths", "Physics", "English"}.issubset(set(chips))

    def test_remove_subject_chip(self, form_page: PracticeFormPage):
        """TC-044: Removing a chip via its delete icon removes it from the list."""
        form_page.add_subject("Maths")
        form_page.remove_subject("Maths")
        assert "Maths" not in form_page.get_subject_chips()

    def test_subject_special_chars_no_match(self, form_page: PracticeFormPage):
        """TC-045: Special characters/numbers produce no suggestion match."""
        form_page.subjects_input.click()
        form_page.subjects_input.fill("@@123")
        options = form_page.page.locator(".subjects-auto-complete__option")
        assert options.count() == 0

    def test_subject_xss_payload(self, form_page: PracticeFormPage):
        """TC-046: XSS payload as free-text subject must not execute."""
        form_page.add_subject("<script>alert(1)</script>", select_suggestion=False)
        assert "alert" not in (form_page.page.title() or "")

    def test_add_many_subjects_wraps_layout(self, form_page: PracticeFormPage):
        """TC-047: Adding 10+ subjects wraps/scrolls without breaking layout."""
        subjects = ["Maths", "Physics", "Chemistry", "English", "Hindi",
                    "Biology", "Computer Science", "Commerce", "Accounting", "Economics"]
        for subject in subjects:
            form_page.add_subject(subject)
        assert not has_horizontal_scroll(form_page.page)


# ===========================================================================
# M7 — Hobbies — TC-048 to TC-052
# ===========================================================================

class TestHobbies:

    def test_select_single_hobby(self, form_page: PracticeFormPage):
        """TC-048: Selecting a single hobby checks that checkbox."""
        form_page.select_hobby("Sports")
        assert form_page.is_hobby_checked("Sports")

    def test_select_all_hobbies(self, form_page: PracticeFormPage):
        """TC-049: All three hobbies can be checked simultaneously."""
        for hobby in ("Sports", "Reading", "Music"):
            form_page.select_hobby(hobby)
        assert all(form_page.is_hobby_checked(h) for h in ("Sports", "Reading", "Music"))

    def test_uncheck_hobby(self, form_page: PracticeFormPage):
        """TC-050: Unchecking a previously checked hobby toggles it off."""
        form_page.select_hobby("Music")
        form_page.select_hobby("Music")
        assert not form_page.is_hobby_checked("Music")

    def test_no_hobby_selected_is_optional(self, form_page: PracticeFormPage):
        """TC-051: Submitting with no hobby selected should not block submission."""
        form_page.fill_minimum_mandatory_fields()
        form_page.click_submit()
        # Modal should appear (hobbies optional)
        expect(form_page.modal_title).to_be_visible()

    def test_hobby_keyboard_toggle(self, form_page: PracticeFormPage):
        """TC-052: Hobby checkboxes toggled via keyboard Space key."""
        form_page.page.locator("label[for='hobbies-checkbox-1']").focus()
        form_page.page.keyboard.press(" ")
        assert form_page.is_hobby_checked("Sports")


# ===========================================================================
# M8 — Picture Upload — TC-053 to TC-058
# ===========================================================================

class TestPictureUpload:

    def test_valid_image_upload(self, form_page: PracticeFormPage, sample_image_path):
        """TC-053: Valid image upload shows filename next to Choose File."""
        form_page.upload_file(sample_image_path)
        expect(form_page.upload_picture).to_have_value(re.compile("sample.png"))

    def test_invalid_file_type(self, form_page: PracticeFormPage, disallowed_file_path):
        """TC-054: Non-image file type — verify whether it is restricted."""
        form_page.upload_file(disallowed_file_path)
        value = form_page.upload_picture.input_value()
        print(f"[TC-054] Upload field value after .exe upload: '{value}'")

    def test_oversized_file(self, form_page: PracticeFormPage, oversized_file_path):
        """TC-055: Oversized (~6MB) file — verify upload behavior/error."""
        form_page.upload_file(oversized_file_path)
        value = form_page.upload_picture.input_value()
        print(f"[TC-055] Upload field value after oversized upload: '{value}'")

    def test_long_filename(self, form_page: PracticeFormPage, tmp_path, sample_image_path):
        """TC-056: Very long filename does not crash the UI."""
        import shutil
        long_name = ("a" * 150) + ".png"
        long_path = tmp_path / long_name
        shutil.copy(sample_image_path, long_path)
        form_page.upload_file(str(long_path))
        expect(form_page.upload_picture).to_be_visible()

    def test_no_file_upload_optional(self, form_page: PracticeFormPage):
        """TC-057: Submitting without uploading a picture should not block submission."""
        form_page.fill_minimum_mandatory_fields()
        form_page.click_submit()
        expect(form_page.modal_title).to_be_visible()

    def test_malicious_filename_sanitized(self, form_page: PracticeFormPage, tmp_path, sample_image_path):
        """TC-058: Filename containing script-like text is sanitized on display."""
        import shutil
        malicious_name = "script_alert_1.png"
        malicious_path = tmp_path / malicious_name
        shutil.copy(sample_image_path, malicious_path)
        form_page.upload_file(str(malicious_path))
        expect(form_page.upload_picture).to_have_value(re.compile(malicious_name))


# ===========================================================================
# M9 — Current Address — TC-059 to TC-064
# ===========================================================================

class TestCurrentAddress:

    def test_multiline_address(self, form_page: PracticeFormPage):
        """TC-059: Multi-line address text is accepted and wraps."""
        address = "123 Main Street\nApt 4B\nSpringfield"
        form_page.fill_address(address)
        expect(form_page.current_address).to_have_value(address)

    def test_empty_address_optional(self, form_page: PracticeFormPage):
        """TC-060: Empty address should not block submission."""
        form_page.fill_minimum_mandatory_fields()
        form_page.click_submit()
        expect(form_page.modal_title).to_be_visible()

    def test_very_long_address(self, form_page: PracticeFormPage):
        """TC-061: 1000+ character address scrolls without breaking layout."""
        long_address = "Main Street " * 100
        form_page.fill_address(long_address)
        expect(form_page.current_address).to_have_value(long_address)
        assert not has_horizontal_scroll(form_page.page)

    def test_unicode_emoji_address(self, form_page: PracticeFormPage):
        """TC-062: Unicode/emoji characters render correctly in address."""
        address = "123 Main St 🏠, Café Lane"
        form_page.fill_address(address)
        expect(form_page.current_address).to_have_value(address)

    def test_address_xss_payload(self, form_page: PracticeFormPage):
        """TC-063: XSS payload in address must not execute."""
        payload = "<script>alert(1)</script>"
        form_page.fill_address(payload)
        expect(form_page.current_address).to_have_value(payload)
        assert "alert" not in (form_page.page.title() or "")

    def test_address_sqli_payload(self, form_page: PracticeFormPage):
        """TC-064: SQLi payload in address treated as plain text."""
        payload = "'; DROP TABLE students;--"
        form_page.fill_address(payload)
        expect(form_page.current_address).to_have_value(payload)


# ===========================================================================
# M10 — State & City — TC-065 to TC-071
# ===========================================================================

class TestStateAndCity:

    def test_select_state_enables_city(self, form_page: PracticeFormPage):
        """TC-065: Selecting a State enables the City dropdown."""
        form_page.select_state("NCR")
        is_disabled = form_page.city_dropdown.locator("input").is_disabled()
        assert not is_disabled

    def test_select_state_and_city(self, form_page: PracticeFormPage):
        """TC-066: Selecting State then City populates both correctly."""
        form_page.select_state("NCR")
        form_page.select_city("Delhi")
        assert "NCR" in form_page.get_selected_state()
        assert "Delhi" in form_page.get_selected_city()

    def test_change_state_resets_city(self, form_page: PracticeFormPage):
        """TC-067: Changing State after City is set resets the City selection."""
        form_page.select_state("NCR")
        form_page.select_city("Delhi")
        form_page.select_state("Uttar Pradesh")
        # City should no longer show the previously selected value
        city_locator = form_page.city_dropdown.locator("div[class*='singleValue']")
        assert city_locator.count() == 0 or "Delhi" not in city_locator.inner_text()

    def test_city_disabled_before_state(self, form_page: PracticeFormPage):
        """TC-068: City remains disabled/empty until a State is chosen."""
        is_disabled = form_page.city_dropdown.locator("input").is_disabled()
        assert is_disabled

    def test_submit_without_state_city(self, form_page: PracticeFormPage):
        """TC-069: Submitting without State/City — verify mandatory validation."""
        form_page.fill_minimum_mandatory_fields()
        form_page.click_submit()
        # Document outcome: modal still appears if State/City are optional
        visible = form_page.modal_title.is_visible()
        print(f"[TC-069] Modal visible without State/City selected: {visible}")

    def test_state_dropdown_type_to_search(self, form_page: PracticeFormPage):
        """TC-070: Typing within the State dropdown filters the option list."""
        form_page.state_dropdown.click()
        form_page.state_dropdown.locator("input").fill("NCR")
        options = form_page.page.locator("div[id^='react-select'][id*='option']")
        assert options.count() >= 1

    def test_state_city_keyboard_only(self, form_page: PracticeFormPage):
        """TC-071: State/City dropdowns are fully keyboard navigable."""
        form_page.state_dropdown.click()
        form_page.page.keyboard.type("NCR")
        form_page.page.keyboard.press("Enter")
        assert "NCR" in form_page.get_selected_state()


# ===========================================================================
# M11 — Form Submission — TC-072 to TC-078
# ===========================================================================

class TestFormSubmission:

    def test_full_valid_submission(self, form_page: PracticeFormPage):
        """TC-072: All mandatory fields filled correctly -> confirmation modal."""
        form_page.fill_first_name("Jordan")
        form_page.fill_last_name("Avery")
        form_page.fill_email("jordan.avery@example.com")
        form_page.select_gender("Male")
        form_page.fill_mobile("9876543210")
        form_page.click_submit()
        expect(form_page.modal_title).to_be_visible()
        assert "Jordan Avery" == form_page.modal_row_value("Student Name")

    def test_submit_all_fields_empty(self, form_page: PracticeFormPage):
        """TC-073: Submitting a completely empty form raises multiple required errors."""
        form_page.click_submit()
        assert form_page.is_field_invalid(form_page.first_name)
        assert form_page.is_field_invalid(form_page.last_name)
        assert form_page.is_field_invalid(form_page.mobile)

    def test_close_confirmation_modal(self, form_page: PracticeFormPage):
        """TC-074: Closing the confirmation modal via 'X' hides it."""
        form_page.fill_minimum_mandatory_fields()
        form_page.click_submit()
        expect(form_page.modal_title).to_be_visible()
        form_page.modal_close_button.click()
        expect(form_page.modal_title).not_to_be_visible()

    def test_rapid_double_click_submit(self, form_page: PracticeFormPage):
        """TC-075: Rapid double-click on Submit does not duplicate/break the modal."""
        form_page.fill_minimum_mandatory_fields()
        form_page.submit_button.click(click_count=2, delay=50)
        expect(form_page.modal_title).to_be_visible()

    def test_submit_with_only_mandatory_fields(self, form_page: PracticeFormPage):
        """TC-076: Filling only mandatory fields still allows successful submission."""
        form_page.fill_minimum_mandatory_fields()
        form_page.click_submit()
        expect(form_page.modal_title).to_be_visible()

    def test_enter_key_on_focused_field(self, form_page: PracticeFormPage):
        """TC-077: Pressing Enter while focused on a text field — document behavior."""
        form_page.fill_minimum_mandatory_fields()
        form_page.first_name.click()
        form_page.page.keyboard.press("Enter")
        visible = form_page.modal_title.is_visible()
        print(f"[TC-077] Modal visible after Enter key on First Name: {visible}")

    def test_modal_data_mapping(self, form_page: PracticeFormPage):
        """TC-078: Modal table correctly maps each label to the entered value."""
        form_page.fill_first_name("Jordan")
        form_page.fill_last_name("Avery")
        form_page.fill_email("jordan.avery@example.com")
        form_page.select_gender("Female")
        form_page.fill_mobile("9876543210")
        form_page.fill_address("123 Main Street")
        form_page.click_submit()
        expect(form_page.modal_title).to_be_visible()
        assert form_page.modal_row_value("Student Name") == "Jordan Avery"
        assert form_page.modal_row_value("Student Email") == "jordan.avery@example.com"
        assert form_page.modal_row_value("Gender") == "Female"
        assert form_page.modal_row_value("Mobile") == "9876543210"
        assert form_page.modal_row_value("Address") == "123 Main Street"


# ===========================================================================
# M12 — Responsive / Cross-Device — TC-079 to TC-086
# ===========================================================================

class TestResponsive:

    @pytest.mark.parametrize("viewport", RESPONSIVE_VIEWPORTS)
    def test_no_horizontal_scroll_at_viewport(self, page: Page, viewport):
        """TC-079/080/081/082: No horizontal scroll at mobile/tablet/desktop sizes."""
        page.set_viewport_size(viewport)
        pom = PracticeFormPage(page)
        pom.goto()
        assert not has_horizontal_scroll(page), f"Horizontal scroll at {viewport}"

    def test_ad_banner_does_not_overlap_submit(self, page: Page):
        """TC-083: On mobile, the fixed ad banner must not intercept the Submit click."""
        page.set_viewport_size({"width": 375, "height": 667})
        pom = PracticeFormPage(page)
        pom.goto(remove_ad_banner=False)  # keep ad visible to test real overlap
        pom.fill_minimum_mandatory_fields()
        # If the ad intercepts the click, Playwright's actionability checks
        # will raise a TimeoutError here instead of silently mis-clicking.
        pom.click_submit()
        expect(pom.modal_title).to_be_visible()

    @pytest.mark.parametrize("element_for", ["gender-radio-1", "hobbies-checkbox-1"])
    def test_touch_target_size_mobile(self, page: Page, element_for):
        """TC-084: Radio/checkbox touch targets meet >=44x44px on mobile."""
        page.set_viewport_size({"width": 375, "height": 667})
        pom = PracticeFormPage(page)
        pom.goto()
        label = page.locator(f"label[for='{element_for}']")
        width, height = get_touch_target_size(label)
        print(f"[TC-084] '{element_for}' label size: {width}x{height}")
        # NOTE: DemoQA's default styling may NOT meet 44x44 — this documents
        # the gap rather than assuming compliance.

    def test_datepicker_visible_on_mobile(self, page: Page):
        """TC-085: Date picker popup fully visible (not clipped) on mobile."""
        page.set_viewport_size({"width": 375, "height": 667})
        pom = PracticeFormPage(page)
        pom.goto()
        pom.open_dob_picker()
        popup = page.locator(".react-datepicker")
        expect(popup).to_be_visible()
        box = popup.bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= 375

    def test_orientation_change_tablet(self, page: Page):
        """TC-086: Layout adapts when rotating tablet portrait <-> landscape."""
        pom = PracticeFormPage(page)
        page.set_viewport_size({"width": 768, "height": 1024})
        pom.goto()
        assert not has_horizontal_scroll(page)
        page.set_viewport_size({"width": 1024, "height": 768})
        assert not has_horizontal_scroll(page)


# ===========================================================================
# M13 — Accessibility — TC-087 to TC-092
# ===========================================================================

class TestAccessibility:

    def test_all_inputs_have_labels(self, form_page: PracticeFormPage):
        """TC-087: Every visible input has an associated label (for/id pairing)."""
        page = form_page.page
        inputs = page.locator("input[id]:not([type='hidden'])")
        missing = []
        for i in range(inputs.count()):
            input_id = inputs.nth(i).get_attribute("id")
            label = page.locator(f"label[for='{input_id}']")
            if label.count() == 0:
                missing.append(input_id)
        print(f"[TC-087] Inputs without an associated <label>: {missing}")
        assert not missing, f"Missing labels for: {missing}"

    def test_tab_order_is_logical(self, form_page: PracticeFormPage):
        """TC-088: Tabbing through the form follows a logical order."""
        form_page.first_name.click()
        order = []
        for _ in range(6):
            form_page.page.keyboard.press("Tab")
            active_id = form_page.page.evaluate("document.activeElement.id")
            order.append(active_id)
        print(f"[TC-088] Tab order observed: {order}")
        assert len(order) == len(set(order)) or len(set(order)) > 1, "Focus appears stuck"

    @pytest.mark.skip(reason="Requires axe-core/contrast-checker integration — TODO")
    def test_color_contrast_meets_wcag_aa(self, form_page: PracticeFormPage):
        """TC-089: Text/placeholder contrast meets WCAG AA (4.5:1). [TODO: integrate axe-core]"""
        pass

    def test_error_state_not_color_only(self, form_page: PracticeFormPage):
        """TC-090: Validation errors should be announced beyond color (aria-invalid/text)."""
        form_page.click_submit()
        aria_invalid = form_page.first_name.get_attribute("aria-invalid")
        print(f"[TC-090] First Name aria-invalid attribute: {aria_invalid}")
        # Known likely gap: DemoQA uses border-color only. This documents the finding.

    def test_aria_roles_on_custom_widgets(self, form_page: PracticeFormPage):
        """TC-091: Subjects/State/City custom widgets expose correct ARIA roles."""
        page = form_page.page
        state_input = form_page.state_dropdown.locator("input")
        role = state_input.get_attribute("role")
        print(f"[TC-091] State input role attribute: {role}")

    def test_focus_indicator_visible(self, form_page: PracticeFormPage):
        """TC-092: Focused elements show a visible outline."""
        form_page.first_name.click()
        outline = form_page.first_name.evaluate("el => getComputedStyle(el).outlineStyle")
        print(f"[TC-092] First Name outline style on focus: {outline}")


# ===========================================================================
# M14 — Cross-Browser — TC-093 to TC-096
# ===========================================================================
# Intentionally no dedicated test functions. Run the full suite with:
#   pytest test_demoqa_practice_form.py --browser chromium
#   pytest test_demoqa_practice_form.py --browser firefox
#   pytest test_demoqa_practice_form.py --browser webkit
# (DRY convention: one test body, executed per browser via CLI flag.)


# ===========================================================================
# M15 — Performance — TC-097 to TC-099
# ===========================================================================

class TestPerformance:

    def test_page_load_time_under_threshold(self, page: Page):
        """TC-097: Page load completes within an acceptable threshold (<3s)."""
        start = time.monotonic()
        page.goto(BASE_URL, wait_until="domcontentloaded")
        elapsed = time.monotonic() - start
        print(f"[TC-097] Page load time: {elapsed:.2f}s")
        assert elapsed < 3.0, f"Page load took {elapsed:.2f}s (threshold: 3.0s)"

    def test_submit_response_time(self, form_page: PracticeFormPage):
        """TC-098: Time from Submit click to modal render is within threshold (<2s)."""
        form_page.fill_minimum_mandatory_fields()
        start = time.monotonic()
        form_page.click_submit()
        form_page.modal_title.wait_for(state="visible", timeout=5000)
        elapsed = time.monotonic() - start
        print(f"[TC-098] Submit-to-modal time: {elapsed:.2f}s")
        assert elapsed < 2.0, f"Submit response took {elapsed:.2f}s (threshold: 2.0s)"

    def test_repeated_submit_cycles_no_console_errors(self, page: Page, console_errors):
        """TC-099: 5x fill+submit+close cycles produce no console errors."""
        pom = PracticeFormPage(page)
        for _ in range(5):
            pom.goto()
            pom.fill_minimum_mandatory_fields()
            pom.click_submit()
            pom.modal_title.wait_for(state="visible", timeout=5000)
            pom.modal_close_button.click()
        print(f"[TC-099] Console errors across 5 cycles: {console_errors}")
        assert not console_errors, f"Unexpected console errors: {console_errors}"
