"""
This module contains classes and functions to parse and validate YAML or JSON input
files. It uses [Pydantic](https://github.com/pydantic/pydantic) to achieve this goal.
All the data classes have `BaseModel` from Pydantic as a base class, and some data
fields have advanced types like `HttpUrl`, `EmailStr`, or `PastDate` from the Pydnatic
library for validation.
"""

from datetime import date as Date
from typing import Literal
from typing_extensions import Annotated, Optional
import re
import logging
from functools import cached_property
import urllib.request

from pydantic import (
    BaseModel,
    HttpUrl,
    Field,
    field_validator,
    model_validator,
    computed_field,
    EmailStr,
    PastDate,
)
from pydantic.functional_validators import AfterValidator
from pydantic_extra_types.phone_numbers import PhoneNumber
from pydantic_extra_types.color import Color

from spellchecker import SpellChecker

# ======================================================================================
# HELPERS ==============================================================================
# ======================================================================================

spell = SpellChecker()

# don't give spelling warnings for these words:
dictionary = [
    "aerostructures",
    "sportsperson",
    "cern",
    "mechatronics",
    "calculix",
    "microcontroller",
    "ansys",
    "nx",
    "aselsan",
    "hrjet",
    "simularge",
    "siemens",
    "dynamometer",
    "dc",
]


def check_spelling(sentence: str) -> str:
    """Check the spelling of a sentence and give warnings if there are any misspelled
    words.

    It uses [pyspellchecker](https://github.com/barrust/pyspellchecker). It can also
    guess the correct version of the misspelled word, but it is not used because it is
    very slow.

    Example:
        ```python
        check_spelling("An interesting sentence is akways good.")
        ```

        will print the following warning:

        `WARNING - The word "akways" might be misspelled according to the pyspellchecker.`

    Args:
        sentence (str): The sentence to check.

    Returns:
        str: The same sentence.
    """
    modifiedSentence = sentence.lower()  # convert to lower case
    modifiedSentence = re.sub(
        r"\-+", " ", modifiedSentence
    )  # replace hyphens with spaces
    modifiedSentence = re.sub(
        r"[^a-z\s\-']", "", modifiedSentence
    )  # remove all the special characters
    words = modifiedSentence.split()  # split sentence into a list of words
    misspelled = spell.unknown(words)  # find misspelled words

    if len(misspelled) > 0:
        for word in misspelled:
            # for each misspelled word, check if it is in the dictionary and otherwise
            # give a warning
            if word in dictionary:
                continue

            logging.warning(
                f'The word "{word}" might be misspelled according to the'
                " pyspellchecker."
            )

    return sentence


def compute_time_span_string(start_date: Date, end_date: Date) -> str:
    """Compute the time span between two dates and return a string that represents it.

    Example:
        ```python
        compute_time_span_string(Date(2022,9,24), Date(2025,2,12))
        ```

        will return:

        `#!python "2 years 5 months"`

    Args:
        start_date (Date): The start date.
        end_date (Date): The end date.

    Returns:
        str: The time span string.
    """
    # check if the types of start_date and end_date are correct:
    if not isinstance(start_date, Date):
        raise TypeError("start_date is not a Date object!")
    if not isinstance(end_date, Date):
        raise TypeError("end_date is not a Date object!")

    # # check if start_date is before end_date:
    if start_date > end_date:
        raise ValueError(
            "The start date is after the end date. Please check the dates!"
        )

    # calculate the number of days between start_date and end_date:
    timespan_in_days = (end_date - start_date).days

    # calculate the number of years between start_date and end_date:
    how_many_years = timespan_in_days // 365
    if how_many_years == 0:
        how_many_years_string = None
    elif how_many_years == 1:
        how_many_years_string = "1 year"
    else:
        how_many_years_string = f"{how_many_years} years"

    # calculate the number of months between start_date and end_date:
    how_many_months = round((timespan_in_days % 365) / 30)
    if how_many_months == 0:
        how_many_months = 1

    if how_many_months == 0:
        how_many_months_string = None
    elif how_many_months == 1:
        how_many_months_string = "1 month"
    else:
        how_many_months_string = f"{how_many_months} months"

    # combine howManyYearsString and howManyMonthsString:
    if how_many_years_string is None:
        timespan_string = how_many_months_string
    elif how_many_months_string is None:
        timespan_string = how_many_years_string
    else:
        timespan_string = f"{how_many_years_string} {how_many_months_string}"

    return timespan_string


def format_date(date: Date) -> str:
    """Formats a date to a string in the following format: "Jan. 2021".

    It uses month abbreviations, taken from
    [Yale University Library](https://web.library.yale.edu/cataloging/months).

    Example:
        ```python
        format_date(Date(2024,5,1))
        ```
        will return

        `#!python "May 2024"`

    Args:
        date (Date): The date to format.

    Returns:
        str: The formatted date.
    """
    # Month abbreviations,
    # taken from: https://web.library.yale.edu/cataloging/months
    abbreviations_of_months = [
        "Jan.",
        "Feb.",
        "Mar.",
        "Apr.",
        "May",
        "June",
        "July",
        "Aug.",
        "Sept.",
        "Oct.",
        "Nov.",
        "Dec.",
    ]

    month = int(date.strftime("%m"))
    monthAbbreviation = abbreviations_of_months[month - 1]
    year = date.strftime("%Y")
    date_string = f"{monthAbbreviation} {year}"

    return date_string


# ======================================================================================
# ======================================================================================
# ======================================================================================

# ======================================================================================
# CUSTOM DATA TYPES ====================================================================
# ======================================================================================

# To understand how to create custom data types, see:
# https://docs.pydantic.dev/latest/usage/types/custom/
LaTeXDimension = Annotated[
    str,
    Field(
        pattern=r"\d+\.?\d* *(cm|in|pt|mm|ex|em)",
        examples=["1.35 cm", "1 in", "12 pt", "14 mm", "2 ex", "3 em"],
    ),
]
SpellCheckedString = Annotated[str, AfterValidator(check_spelling)]

# ======================================================================================
# ======================================================================================
# ======================================================================================

# ======================================================================================
# DESIGN MODELS ========================================================================
# ======================================================================================


class ClassicThemePageMargins(BaseModel):
    """This class stores the margins of pages for the classic theme."""

    top: LaTeXDimension = Field(
        default="1.35 cm",
        title="Top Margin",
        description="The top margin of the page.",
    )
    bottom: LaTeXDimension = Field(
        default="1.35 cm",
        title="Bottom Margin",
        description="The bottom margin of the page.",
    )
    left: LaTeXDimension = Field(
        default="1.35 cm",
        title="Left Margin",
        description="The left margin of the page.",
    )
    right: LaTeXDimension = Field(
        default="1.35 cm",
        title="Right Margin",
        description="The right margin of the page.",
    )


class ClassicThemeSectionTitleMargins(BaseModel):
    """This class stores the margins of section titles for the classic theme."""

    top: LaTeXDimension = Field(
        default="0.13 cm",
        title="Top Margin",
        description="The top margin of section titles.",
    )
    bottom: LaTeXDimension = Field(
        default="0.13 cm",
        title="Bottom Margin",
        description="The bottom margin of section titles.",
    )


class ClassicThemeEntryAreaMargins(BaseModel):
    """This class stores the margins of entry areas for the classic theme.

    For the classic theme, entry areas are (OneLineEntry)[../index.md#onelineentry],
    (NormalEntry)[../index.md#normalentry], and
    (ExperienceEntry)[../index.md#experienceentry].
    """

    left: LaTeXDimension = Field(
        default="0.2 cm",
        title="Left Margin",
        description="The left margin of entry areas.",
    )
    right: LaTeXDimension = Field(
        default="0.2 cm",
        title="Right Margin",
        description="The right margin of entry areas.",
    )

    vertical_between: LaTeXDimension = Field(
        default="0.12 cm",
        title="Vertical Margin Between Entry Areas",
        description="The vertical margin between entry areas.",
    )


class ClassicThemeHighlightsAreaMargins(BaseModel):
    """This class stores the margins of highlights areas for the classic theme."""

    top: LaTeXDimension = Field(
        default="0.12 cm",
        title="Top Margin",
        description="The top margin of highlights areas.",
    )
    left: LaTeXDimension = Field(
        default="0.6 cm",
        title="Left Margin",
        description="The left margin of highlights areas.",
    )
    vertical_between_bullet_points: LaTeXDimension = Field(
        default="0.07 cm",
        title="Vertical Margin Between Bullet Points",
        description="The vertical margin between bullet points.",
    )


class ClassicThemeMargins(BaseModel):
    """This class stores the margins for the classic theme."""

    page: ClassicThemePageMargins = Field(
        default=ClassicThemePageMargins(),
        title="Page Margins",
    )
    section_title: ClassicThemeSectionTitleMargins = Field(
        default=ClassicThemeSectionTitleMargins(),
        title="Section Title Margins",
    )
    entry_area: ClassicThemeEntryAreaMargins = Field(
        default=ClassicThemeEntryAreaMargins(),
        title="Entry Area Margins",
    )
    highlights_area: ClassicThemeHighlightsAreaMargins = Field(
        default=ClassicThemeHighlightsAreaMargins(),
        title="Highlights Area Margins",
    )


class ClassicThemeOptions(BaseModel):
    """This class stores the options for the classic theme.

    In RenderCV, each theme has its own Pydantic class so that new themes
    can be implemented easily in future.
    """

    primary_color: Color = Field(
        default="rgb(0,79,144)",
        validate_default=True,
        title="Primary Color",
        description=(
            "The primary color of Classic Theme. It is used for the section titles,"
            " heading, and the links.\nThe color can be specified either with their"
            " [name](https://www.w3.org/TR/SVG11/types.html#ColorKeywords), hexadecimal"
            " value, RGB value, or HSL value."
        ),
        examples=["Black", "7fffd4", "rgb(0,79,144)", "hsl(270, 60%, 70%)"],
    )

    date_and_location_width: LaTeXDimension = Field(
        default="3.7 cm",
        title="Date and Location Column Width",
        description="The width of the date and location column.",
        examples=["1.35 cm", "1 in", "12 pt", "14 mm", "2 ex", "3 em"],
    )

    show_timespan_in_experience_entries: bool = Field(
        default=True,
        title="Show Time Span in Experience Entries",
        description=(
            "If this option is set to true, then the time span of the experience"
            " entries will be shown in the date and location column."
        ),
    )

    show_last_updated_date: bool = Field(
        default=True,
        title="Show Last Updated Date",
        description=(
            "If this option is set to true, then the last updated date will be shown"
            " in the header."
        ),
    )

    margins: ClassicThemeMargins = Field(
        default=ClassicThemeMargins(),
        title="Margins",
        description="Page, section title, entry field, and highlights field margins.",
    )


class Design(BaseModel):
    """This class stores the theme name of the CV and the theme's options."""

    theme: Literal["classic"] = Field(
        default="classic",
        title="Theme name",
        description='The only option is "Classic" for now.',
    )
    options: ClassicThemeOptions = Field(
        default=ClassicThemeOptions(),
        title="Theme Options",
        description="The options of the theme.",
    )


# ======================================================================================
# ======================================================================================
# ======================================================================================

# ======================================================================================
# CONTENT MODELS =======================================================================
# ======================================================================================


class Event(BaseModel):
    """This class is the parent class for classes like `#!python EducationEntry`,
    `#!python ExperienceEntry`, `#!python NormalEntry`, and `#!python OneLineEntry`.

    It stores the common fields between these classes like dates, location, highlights,
    and URL.
    """

    start_date: Optional[PastDate] = Field(
        default=None,
        title="Start Date",
        description="The start date of the event in YYYY-MM-DD format.",
        examples=["2020-09-24"],
    )
    end_date: Optional[PastDate | Literal["present"]] = Field(
        default=None,
        title="End Date",
        description=(
            "The end date of the event in YYYY-MM-DD format. If the event is still"
            ' ongoing, then the value should be "present".'
        ),
        examples=["2020-09-24", "present"],
    )
    date: Optional[str | PastDate] = Field(
        default=None,
        title="Date",
        description=(
            "If the event is a one-day event, then this field should be filled in"
            " YYYY-MM-DD format. If the event is a multi-day event, then the start date"
            " and end date should be provided instead. All of them can't be provided at"
            " the same time."
        ),
        examples=["2020-09-24"],
    )
    highlights: Optional[list[SpellCheckedString]] = Field(
        default=[],
        title="Highlights",
        description=(
            "The highlights of the event. It will be rendered as bullet points."
        ),
        examples=["Did this.", "Did that."],
    )
    location: Optional[str] = Field(
        default=None,
        title="Location",
        description=(
            "The location of the event. It will be shown with the date in the"
            " same column."
        ),
        examples=["Istanbul, Turkey"],
    )
    url: Optional[HttpUrl] = None

    @field_validator("date")
    @classmethod
    def check_date(cls, date: str | PastDate) -> str | PastDate:
        if isinstance(date, str):
            try:
                # If this runs, it means the date is an ISO format string, and it can be
                # parsed
                date = Date.fromisoformat(date)
            except ValueError:
                # Then it means it is a custom string like "Fall 2023"
                date = date

        return date

    @model_validator(mode="after")
    @classmethod
    def check_dates(cls, model):
        """Make sure that either `#!python start_date` and `#!python end_date` or only
        `#!python date`is provided.
        """
        date_is_provided = False
        start_date_is_provided = False
        end_date_is_provided = False
        if model.date is not None:
            date_is_provided = True
        if model.start_date is not None:
            start_date_is_provided = True
        if model.end_date is not None:
            end_date_is_provided = True

        if date_is_provided and start_date_is_provided and end_date_is_provided:
            logging.warning(
                '"start_date", "end_date" and "date" are all provided in of the'
                " entries. Therefore, date will be ignored."
            )
            model.date = None

        elif date_is_provided and start_date_is_provided and not end_date_is_provided:
            logging.warning(
                'Both "date" and "start_date" is provided in of the entries.'
                ' "start_date" will be ignored.'
            )
            model.start_date = None
            model.end_date = None

        elif date_is_provided and end_date_is_provided and not start_date_is_provided:
            logging.warning(
                'Both "date" and "end_date" is provided in of the entries. "end_date"'
                " will be ignored."
            )
            model.start_date = None
            model.end_date = None

        elif start_date_is_provided and not end_date_is_provided:
            logging.warning(
                '"start_date" is provided in of the entries, but "end_date" is not.'
                ' "end_date" will be set to "present".'
            )
            model.end_date = "present"

        if model.start_date is not None and model.end_date is not None:
            if model.end_date == "present":
                end_date = Date.today()
            else:
                end_date = model.end_date

            if model.start_date > end_date:
                raise ValueError(
                    '"start_date" is after "end_date". Please check the dates!'
                )

        return model

    @computed_field
    @cached_property
    def date_and_location_strings_with_timespan(self) -> list[str]:
        date_and_location_strings = []

        if self.location is not None:
            date_and_location_strings.append(self.location)

        if self.date is not None:
            if isinstance(self.date, str):
                date_and_location_strings.append(self.date)
            elif isinstance(self.date, Date):
                date_and_location_strings.append(format_date(self.date))
            else:
                raise RuntimeError("Date is neither a string nor a Date object!")
        elif self.start_date is not None and self.end_date is not None:
            start_date = format_date(self.start_date)

            if self.end_date == "present":
                end_date = "present"

                time_span_string = compute_time_span_string(
                    self.start_date, Date.today()
                )
            else:
                end_date = format_date(self.end_date)

                time_span_string = compute_time_span_string(
                    self.start_date, self.end_date
                )

            date_and_location_strings.append(f"{start_date} to {end_date}")

            date_and_location_strings.append(f"{time_span_string}")

        return date_and_location_strings

    @computed_field
    @cached_property
    def date_and_location_strings_without_timespan(self) -> list[str]:
        # use copy() to avoid modifying the original list
        date_and_location_strings = self.date_and_location_strings_with_timespan.copy()
        for string in date_and_location_strings:
            if (
                "years" in string
                or "months" in string
                or "year" in string
                or "month" in string
            ):
                date_and_location_strings.remove(string)

        return date_and_location_strings

    @computed_field
    @cached_property
    def highlight_strings(self) -> list[SpellCheckedString]:
        highlight_strings = []
        if self.highlights is not None:
            highlight_strings.extend(self.highlights)

        return highlight_strings

    @computed_field
    @cached_property
    def markdown_url(self) -> Optional[str]:
        if self.url is None:
            return None
        else:
            url = str(self.url)

            if "github" in url:
                link_text = "view on GitHub"
            elif "linkedin" in url:
                link_text = "view on LinkedIn"
            elif "instagram" in url:
                link_text = "view on Instagram"
            elif "youtube" in url:
                link_text = "view on YouTube"
            else:
                link_text = "view on my website"

            markdown_url = f"[{link_text}]({url})"

            return markdown_url

    @computed_field
    @cached_property
    def month_and_year(self) -> Optional[str]:
        if self.date is not None:
            # Then it means start_date and end_date are not provided.
            try:
                # If this runs, it means the date is an ISO format string, and it can be
                # parsed
                month_and_year = format_date(self.date)
            except:
                month_and_year = self.date
        else:
            # Then it means start_date and end_date are provided and month_and_year
            # doesn't make sense.
            month_and_year = None

        return month_and_year


class OneLineEntry(Event):
    """This class stores [OneLineEntry](../index.md#onelineentry) information."""

    name: str = Field(
        title="Name",
        description="The name of the entry. It will be shown as bold text.",
    )
    details: str = Field(
        title="Details",
        description="The details of the entry. It will be shown as normal text.",
    )


class NormalEntry(Event):
    """This class stores [NormalEntry](../index.md#normalentry) information."""

    name: str = Field(
        title="Name",
        description="The name of the entry. It will be shown as bold text.",
    )


class ExperienceEntry(Event):
    """This class stores [ExperienceEntry](../index.md#experienceentry) information."""

    company: str = Field(
        title="Company",
        description="The company name. It will be shown as bold text.",
        examples=["CERN", "Apple"],
    )
    position: str = Field(
        title="Position",
        description="The position. It will be shown as normal text.",
        examples=["Software Engineer", "Mechanical Engineer"],
    )


class EducationEntry(Event):
    """This class stores [EducationEntry](../index.md#educationentry) information."""

    # 1) Mandotory user inputs:
    institution: str = Field(
        title="Institution",
        description="The institution name. It will be shown as bold text.",
        examples=["Massachusetts Institute of Technology", "Bogazici University"],
    )
    area: str = Field(
        title="Area",
        description="The area of study. It will be shown as normal text.",
        examples=["Mechanical Engineering", "Computer Science"],
    )
    # 2) Optional user inputs:
    study_type: Optional[str] = Field(
        default=None,
        title="Study Type",
        description="The type of the degree.",
        examples=["BS", "BA", "PhD", "MS"],
    )
    gpa: Optional[str | float] = Field(
        default=None,
        title="GPA",
        description="The GPA of the degree.",
        examples=["4.00/4.00", "3.80/4.00"],
    )
    transcript_url: Optional[HttpUrl] = Field(
        default=None,
        title="Transcript URL",
        description=(
            "The URL of the transcript. It will be shown as a link next to the GPA."
        ),
        examples=["https://example.com/transcript.pdf"],
    )

    @computed_field
    @cached_property
    def highlight_strings(self) -> list[SpellCheckedString]:
        highlight_strings = []

        if self.gpa is not None:
            gpaString = f"GPA: {self.gpa}"
            if self.transcript_url is not None:
                gpaString += f" ([Transcript]({self.transcript_url}))"
            highlight_strings.append(gpaString)

        if self.highlights is not None:
            highlight_strings.extend(self.highlights)

        return highlight_strings


class PublicationEntry(Event):
    """This class stores [PublicationEntry](../index.md#publicationentry) information."""

    title: str = Field(
        title="Title of the Publication",
        description="The title of the publication. It will be shown as bold text.",
        examples=["My Awesome Paper", "My Awesome Book"],
    )
    authors: list[str] = Field(
        title="Authors",
        description="The authors of the publication in order as a list of strings.",
        examples=["John Doe", "Jane Doe"],
    )
    doi: str = Field(
        title="DOI",
        description="The DOI of the publication.",
        examples=["10.1103/PhysRevB.76.054309"],
    )
    date: str = Field(
        title="Publication Date",
        description="The date of the publication.",
        examples=[2021, 2022],
    )
    cited_by: Optional[int] = Field(
        default=None,
        title="Cited By",
        description="The number of citations of the publication.",
        examples=[10, 100],
    )
    journal: Optional[str] = Field(
        default=None,
        title="Journal",
        description="The journal or the conference name.",
        examples=[
            "Physical Review B",
            "ASME International Mechanical Engineering Congress and Exposition",
        ],
    )

    @field_validator("doi")
    @classmethod
    def check_doi(cls, doi: str) -> str:
        doi_url = f"https://doi.org/{doi}"

        try:
            urllib.request.urlopen(doi_url)
        except:
            raise ValueError(f"{doi} cannot be found in the DOI System.")

        return doi

    @computed_field
    @cached_property
    def doi_url(self) -> str:
        return f"https://doi.org/{self.doi}"


class SocialNetwork(BaseModel):
    """This class stores a social network information.

    Currently, only LinkedIn, Github, and Instagram are supported.
    """

    network: Literal["LinkedIn", "GitHub", "Instagram"] = Field(
        title="Social Network",
        description="The social network name.",
        examples=["LinkedIn", "GitHub", "Instagram"],
    )
    username: str = Field(
        title="Username",
        description="The username of the social network. The link will be generated.",
        examples=["johndoe", "johndoe123"],
    )


class Connection(BaseModel):
    r"""This class stores a connection/communication information.

    Warning:
        This class isn't designed for users to use, but it is used by RenderCV to make
        the $\LaTeX$ templating easier.
    """

    name: Literal[
        "LinkedIn", "GitHub", "Instagram", "phone", "email", "website", "location"
    ]
    value: str

    @field_validator("value")
    @classmethod
    def check_type_of_value(cls, value: str) -> str:
        if not re.search(r"[^\d\-+]", str(value)):
            # If there is nothing other than digits, hyphens, and plus signs, then it is
            # a phone number
            value = "tel:" + value

        return value

    @computed_field
    @cached_property
    def url(self) -> HttpUrl:
        if self.name == "LinkedIn":
            url = f"https://www.linkedin.com/in/{self.value}"
        elif self.name == "GitHub":
            url = f"https://www.github.com/{self.value}"
        elif self.name == "Instagram":
            url = f"https://www.instagram.com/{self.value}"
        elif self.name == "email":
            url = f"mailto:{self.value}"
        elif self.name == "website":
            url = self.value
        elif self.name == "phone":
            url = self.value
        elif self.name == "location":
            url = None
        else:
            raise RuntimeError(f'"{self.name}" is not a valid connection!"')

        return url


class Section(BaseModel):
    """This class stores a section information."""

    title: str = Field(
        title="Section Title",
        description="The title of the section.",
        examples=["Awards", "My Custom Section", "Languages"],
    )
    entry_type: Literal[
        "OneLineEntry",
        "NormalEntry",
        "ExperienceEntry",
        "EducationEntry",
        "PublicationEntry",
    ] = Field(
        title="Entry Type",
        description="The type of the entries in the section.",
    )
    link_text: Optional[str] = Field(
        default=None,
        title="Link Text",
        description=(
            "If the section has a link, then what should be the text of the link? If"
            " this field is not provided, then the link text will be generated"
            " automatically based on the URL."
        ),
        examples=["view on GitHub", "view on LinkedIn"],
    )
    entries: list[
        NormalEntry | OneLineEntry | ExperienceEntry | EducationEntry | PublicationEntry
    ] = Field(
        title="Entries",
        description="The entries of the section. The format depends on the entry type.",
    )

    @field_validator("title")
    @classmethod
    def make_first_letters_uppercase(cls, title: str) -> str:
        return title.title()


class CurriculumVitae(BaseModel):
    """This class bindes all the information of a CV together."""

    # 1) Mandotory user inputs:
    name: str = Field(
        title="Name",
        description="The name of the person.",
        examples=["John Doe", "Jane Doe"],
    )
    # 2) Optional user inputs:
    label: Optional[str] = Field(
        default=None,
        title="Label",
        description="The label of the person.",
        examples=["Software Engineer", "Mechanical Engineer"],
    )
    location: Optional[str] = Field(
        default=None,
        title="Location",
        description="The location of the person. This is not rendered currently.",
        examples=["Istanbul, Turkey", "Boston, MA, USA"],
    )
    email: Optional[EmailStr] = Field(
        default=None,
        title="Email",
        description="The email of the person. It will be rendered in the heading.",
    )
    phone: Optional[PhoneNumber] = None
    website: Optional[HttpUrl] = None
    section_order: Optional[list[str]] = Field(
        default=None,
        title="Section Order",
        description=(
            "The order of sections in the CV. The section title should be used."
        ),
        examples=[["Education", "Work Experience", "Skills"]],
    )
    social_networks: Optional[list[SocialNetwork]] = Field(
        default=None,
        title="Social Networks",
        description=(
            "The social networks of the person. They will be rendered in the heading."
        ),
    )
    education: Optional[list[EducationEntry]] = Field(
        default=None,
        title="Education",
        description="The education entries of the person.",
    )
    work_experience: Optional[list[ExperienceEntry]] = Field(
        default=None,
        title="Work Experience",
        description="The work experience entries of the person.",
    )
    academic_projects: Optional[list[NormalEntry]] = Field(
        default=None,
        title="Academic Projects",
        description="The academic project entries of the person.",
    )
    personal_projects: Optional[list[NormalEntry]] = Field(
        default=None,
        title="Personal Projects",
        description="The personal project entries of the person.",
    )
    publications: Optional[list[PublicationEntry]] = Field(
        default=None,
        title="Publications",
        description="The publication entries of the person.",
    )
    certificates: Optional[list[NormalEntry]] = Field(
        default=None,
        title="Certificates",
        description="The certificate entries of the person.",
    )
    extracurricular_activities: Optional[list[ExperienceEntry]] = Field(
        default=None,
        title="Extracurricular Activities",
        description="The extracurricular activity entries of the person.",
    )
    test_scores: Optional[list[OneLineEntry]] = Field(
        default=None,
        title="Test Scores",
        description="The test score entries of the person.",
    )
    skills: Optional[list[OneLineEntry]] = Field(
        default=None,
        title="Skills",
        description="The skill entries of the person.",
    )
    custom_sections: Optional[list[Section]] = Field(
        default=None,
        title="Custom Sections",
        description=(
            "Custom sections with custom section titles can be rendered as well."
        ),
    )

    @model_validator(mode="after")
    @classmethod
    def check_if_the_section_names_are_unique(self, model):
        pre_defined_section_names = [
            "Education",
            "Work Experience",
            "Academic Projects",
            "Personal Projects",
            "Certificates",
            "Extracurricular Activities",
            "Test Scores",
            "Skills",
            "Publications",
        ]
        if model.custom_sections is not None:
            custom_section_names = []
            for custom_section in model.custom_sections:
                custom_section_names.append(custom_section.title)

        section_names = pre_defined_section_names + custom_section_names
        seen = set()
        duplicates = {val for val in section_names if (val in seen or seen.add(val))}
        if len(duplicates) > 0:
            raise ValueError(
                "The section names should be unique. The following section names are"
                f" duplicated: {duplicates}"
            )

        return model

    @computed_field
    @cached_property
    def connections(self) -> list[str]:
        connections = []
        if self.location is not None:
            connections.append(Connection(name="location", value=self.location))
        if self.phone is not None:
            connections.append(Connection(name="phone", value=self.phone))
        if self.email is not None:
            connections.append(Connection(name="email", value=self.email))
        if self.website is not None:
            connections.append(Connection(name="website", value=str(self.website)))
        if self.social_networks is not None:
            for social_network in self.social_networks:
                connections.append(
                    Connection(
                        name=social_network.network, value=social_network.username
                    )
                )

        return connections

    @computed_field
    @cached_property
    def sections(self) -> list[Section]:
        sections = []

        # Pre-defined sections (i.e. sections that are not custom)):
        pre_defined_sections = {
            "Education": self.education,
            "Work Experience": self.work_experience,
            "Academic Projects": self.academic_projects,
            "Personal Projects": self.personal_projects,
            "Certificates": self.certificates,
            "Extracurricular Activities": self.extracurricular_activities,
            "Test Scores": self.test_scores,
            "Skills": self.skills,
            "Publications": self.publications,
        }

        if self.section_order is None:
            # If the user didn't specify the section order, then use the default order:
            self.section_order = [
                "Education",
                "Work Experience",
                "Academic Projects",
                "Personal Projects",
                "Skills",
                "Test Scores",
                "Certificates",
                "Extracurricular Activities",
                "Publications",
            ]
            if self.custom_sections is not None:
                # If the user specified custom sections, then add them to the end of the
                # section order with the same order as they are in the input file:
                self.section_order.extend(
                    [section.title for section in self.custom_sections]
                )

        link_text = None
        for section_name in self.section_order:
            # Create a section for each section name in the section order:
            if section_name in pre_defined_sections:
                if pre_defined_sections[section_name] is None:
                    continue

                entry_type = pre_defined_sections[section_name][0].__class__.__name__
                entries = pre_defined_sections[section_name]
                if section_name == "Test Scores":
                    link_text = "view score report"
            else:
                # If the section is not pre-defined, then it is a custom section.
                # Find the corresponding custom section and get its entries:
                if self.custom_sections is None:
                    raise ValueError(
                        f'"{section_name}" is not a valid section name. Please create a'
                        " custom section with this name or delete it from the section"
                        " order."
                    )
                else:
                    for custom_section in self.custom_sections:
                        if custom_section.title == section_name:
                            entry_type = custom_section.entries[0].__class__.__name__
                            entries = custom_section.entries
                            break

            section = Section(
                title=section_name,
                entry_type=entry_type,  # type: ignore
                entries=entries,  # type: ignore
                link_text=link_text,
            )
            sections.append(section)

        return sections


# ======================================================================================
# ======================================================================================
# ======================================================================================


class RenderCVDataModel(BaseModel):
    """This class binds both the CV and the design information together."""

    design: Design
    cv: CurriculumVitae