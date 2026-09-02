"""Tests for the South African normalisation rules.

These are the parts of the ingest pipeline that encode local knowledge —
province names, youth programmes, entry-level phrasing — and they are all
heuristics over free text, so they need pinning down.
"""

import pytest

from app.jobs.sources.base import (
    NormalisedJob,
    detect_opportunity_type,
    looks_remote,
    normalise_province,
    requires_no_experience,
)


class TestProvince:
    @pytest.mark.parametrize(
        "location, expected",
        [
            ("Cape Town, Western Cape", "Western Cape"),
            ("Sandton", "Gauteng"),
            ("Pretoria, Tshwane", "Gauteng"),
            ("Umhlanga", "KwaZulu-Natal"),
            ("Durban, KZN", "KwaZulu-Natal"),
            ("Gqeberha", "Eastern Cape"),
            ("Bloemfontein", "Free State"),
            ("Upington", "Northern Cape"),
            ("Cape Town City Centre, Cape Town Region", "Western Cape"),
            ("Mpumalanga, South Africa", "Mpumalanga"),
        ],
    )
    def test_recognises_sa_locations(self, location, expected):
        assert normalise_province(location) == expected

    def test_east_london_is_not_shadowed_by_london(self):
        # Longest-match-first matters: "london" must not win over "east london".
        assert normalise_province("East London") == "Eastern Cape"

    @pytest.mark.parametrize("location", [None, "", "Nairobi, Kenya", "Remote"])
    def test_unknown_locations_have_no_province(self, location):
        assert normalise_province(location) is None


class TestRemote:
    @pytest.mark.parametrize(
        "text", ["Fully Remote, South Africa", "Work from home", "Hybrid - Cape Town"]
    )
    def test_detects_remote(self, text):
        assert looks_remote(text) is True

    def test_office_role_is_not_remote(self):
        assert looks_remote("Sandton, Gauteng") is False


class TestOpportunityType:
    @pytest.mark.parametrize(
        "title, expected",
        [
            ("Contact Centre Learnership Programme", "Learnership"),
            ("Data Engineer Graduate Programme", "Graduate programme"),
            ("Graduate Trainee Planner", "Graduate programme"),
            ("HR Intern", "Internship"),
            ("Internship: Human Resources", "Internship"),
            ("Junior Electrical Apprentice", "Apprenticeship"),
            ("Software Developer", "Job"),
        ],
    )
    def test_classifies_from_title(self, title, expected):
        assert detect_opportunity_type(title, "") == expected

    @pytest.mark.parametrize(
        "title", ["Internal Auditor", "International Sales Manager", "Internal Comms Lead"]
    )
    def test_word_boundaries_prevent_false_internships(self, title):
        assert detect_opportunity_type(title, "Manage internal processes.") == "Job"

    def test_programme_named_as_a_requirement_is_still_a_job(self):
        # "Completed internship or 1 year's experience" describes the candidate,
        # not the role on offer.
        assert (
            detect_opportunity_type(
                "Accountant",
                "Minimum Requirements: Degree. Completed internship or minimum "
                "1 year's experience in financial reporting.",
            )
            == "Job"
        )

    def test_programme_mentioned_late_in_boilerplate_is_ignored(self):
        description = "We are a large firm. " * 40 + "We also run an internship programme."
        assert detect_opportunity_type("Accountant", description) == "Job"

    def test_programme_described_up_front_counts(self):
        assert (
            detect_opportunity_type(
                "Retail Assistant",
                "A 12 month learnership opportunity for unemployed youth.",
            )
            == "Learnership"
        )


class TestNoExperience:
    @pytest.mark.parametrize(
        "text",
        [
            "No experience required",
            "Training provided, matric only",
            "Full training given to the successful candidate",
        ],
    )
    def test_detects_open_to_beginners(self, text):
        assert requires_no_experience("Sales Agent", text) is True

    def test_senior_role_is_not_flagged(self):
        assert requires_no_experience("Senior Engineer", "5+ years required") is False


class TestNormalisedJob:
    def _job(self, **kwargs) -> NormalisedJob:
        defaults = dict(
            source="test", source_id="1", apply_url="https://example.com", title="Role",
            company="Co",
        )
        return NormalisedJob(**{**defaults, **kwargs})

    def test_derives_province_from_location(self):
        assert self._job(location="Sandton, Gauteng").province == "Gauteng"

    def test_youth_programmes_are_entry_level_by_default(self):
        job = self._job(title="Contact Centre Learnership")
        assert job.opportunity_type == "Learnership"
        assert job.experience_level == "Entry"

    def test_no_experience_roles_are_entry_level(self):
        job = self._job(title="Sales Agent", description="No experience required.")
        assert job.no_experience_required is True
        assert job.experience_level == "Entry"

    def test_explicit_experience_level_is_not_overwritten(self):
        job = self._job(title="Intern", experience_level="Intermediate")
        assert job.experience_level == "Intermediate"
