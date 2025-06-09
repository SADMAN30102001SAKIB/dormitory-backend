# This script will first handle finding and downloading the PDFs.

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import pytesseract
from pdf2image import convert_from_path
import tempfile
import os

from langchain_google_genai import ChatGoogleGenerativeAI
from django.conf import settings
from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from posts.models import Post, Tag


# Base URL for the scholarship page
SHED_BASE_URL = "https://shed.gov.bd"
SCHOLARSHIP_PAGE_URL = f"{SHED_BASE_URL}/site/view/scholarship/%E0%A6%B6%E0%A6%BF%E0%A6%95%E0%A7%8D%E0%A6%B7%E0%A6%BE%E0%A6%AC%E0%A7%83%E0%A6%A4%E0%A7%8D%E0%A6%A4%E0%A6%BF-%E0%A6%AC%E0%A6%BF%E0%A6%9C%E0%A7%8D%E0%A6%9E%E0%A6%AA%E0%A7%8D%E0%A6%A4%E0%A6%BF"


def find_scholarship_links():
    """Finds all PDF links on the scholarship page."""
    try:
        response = requests.get(SCHOLARSHIP_PAGE_URL)
        response.raise_for_status()  # Ensure we raise an error for bad responses
        soup = BeautifulSoup(response.content, "html.parser")

        # This selector targets the links within the main content area.
        # You may need to adjust this if the website structure changes.
        notice_links = soup.select("td a[href*='.pdf']")
        """
        This selector looks for <a> tags within <td> elements that have an href attribute containing '.pdf'. *=  operates like a wildcard, matching any href that includes '.pdf'.
        This is a common pattern for links to PDF files, but you may need to adjust it based on the actual HTML structure of the page.
        """

        pdf_urls = []
        for link in notice_links:
            relative_url = link.get("href")  # Get the href attribute of the link
            # absolute_url = urljoin(SHED_BASE_URL, relative_url)
            if relative_url:  # Ensure relative_url is not None
                relative_url = relative_url.lstrip("/")  # Remove leading slashes
                if not relative_url.startswith(("http://", "https://")):
                    relative_url = "https://" + relative_url

            pdf_urls.append(relative_url)

        return pdf_urls
    except requests.RequestException as e:
        print(f"Error fetching scholarship page: {e}")
        return []


def extract_text_from_pdf(pdf_path):
    """Extracts text from an image-based PDF using OCR."""
    text_content = ""
    try:
        # Convert PDF to a list of images to perform OCR
        images = convert_from_path(pdf_path)
        for i, image in enumerate(images):
            # Use Tesseract to do OCR on the image. 'ben+eng' supports both Bengali and English.
            text = pytesseract.image_to_string(image, lang="ben+eng")
            text_content += f"\n--- Page {i+1} ---\n{text}"
        return text_content
    except Exception as e:
        print(f"Error during OCR processing: {e}")
        return None


class ScholarshipInfo(BaseModel):
    title: str = Field(
        description="A concise and attractive title for the scholarship notice."
    )
    summary: str = Field(
        description="A detailed summary of the scholarship. Include eligibility, deadline, application process, and benefits. Format this in Markdown for readability."
    )
    tags: list[str] = Field(
        description="A list of 3-5 relevant tags in lowercase. For example: ['undergraduate', 'government', 'engineering', 'international']."
    )


def get_structured_opportunity(text_content: str) -> ScholarshipInfo | None:
    """Uses an LLM to extract structured data from raw text."""
    try:
        # Set up the parser
        parser = PydanticOutputParser(pydantic_object=ScholarshipInfo)

        # Initialize the language model with Gemini
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-preview-05-20",
            api_key=settings.GEMINI_API_KEY,
            temperature=0,  # Set to 0 for deterministic output
        )

        # Create the prompt template
        prompt_template = """
        You are an expert assistant for the 'Dormitory' student platform. Your task is to analyze the following text from a scholarship notice and extract key information in a structured format. The text is from an OCR process and may contain errors. The text is in both English and Bengali.

        Please extract the following:
        1.  A clear and engaging title for the post.
        2.  A comprehensive summary in Markdown format. The summary must include:
            -   Eligibility requirements (e.g., academic level, field of study).
            -   The application deadline.
            -   A brief on the application procedure.
            -   Mention the scholarship benefits if available.
        3.  A list of 3-5 relevant tags (e.g., 'masters', 'research', 'japan', 'government_funded').

        {format_instructions}

        Here is the OCR text from the scholarship notice:
        ---
        {ocr_text}
        ---
        """
        prompt = ChatPromptTemplate.from_template(
            template=prompt_template,
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        """
        2.  **`partial_variables`**:
            *   The `partial_variables` argument in `ChatPromptTemplate.from_template` allows you to "pre-fill" some of the variables in your prompt template.
            *   In this case, `{"format_instructions": parser.get_format_instructions()}` means that the `{format_instructions}` placeholder in the template string will always be filled with the output of `parser.get_format_instructions()`.
            *   This is useful when a part of your prompt is static or derived from a fixed source (like the parser's instructions) and doesn't change with each invocation of the chain. It simplifies the `chain.invoke()` call later, as you only need to provide the variables that change, like `ocr_text`.
        """

        # Create the chain and run it
        chain = prompt | llm | parser
        result = chain.invoke({"ocr_text": text_content})
        return result
    except Exception as e:
        print(f"Error communicating with LLM: {e}")
        return None


class Command(BaseCommand):
    help = (
        "Scrapes scholarship notices, processes them, and posts them to the platform."
    )

    def handle(self, *args, **options):
        self.stdout.write("Starting scholarship scraping process...")

        # 1. Get the Bot User
        try:
            bot_user = User.objects.get(username="dormitory_kitten")
        except User.DoesNotExist:
            self.stderr.write(
                self.style.ERROR(
                    "Bot user 'dormitory_kitten' not found. Please create it."
                )
            )
            return

        # 2. Find all scholarship PDF links
        pdf_urls = find_scholarship_links()
        if not pdf_urls:
            self.stdout.write("No new scholarship PDFs found.")
            return

        self.stdout.write(f"Found {len(pdf_urls)} potential scholarship notices.")

        for url in pdf_urls:
            # 3. Check if this scholarship has already been posted
            if Post.objects.filter(source_url=url).exists():
                self.stdout.write(
                    self.style.WARNING(f"Skipping already posted scholarship: {url}")
                )
                continue

            self.stdout.write(f"Processing new scholarship: {url}")

            try:
                # 4. Download the PDF to a temporary file
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".pdf"
                ) as temp_pdf:
                    response = requests.get(url)
                    response.raise_for_status()
                    temp_pdf.write(response.content)
                    pdf_path = temp_pdf.name

                # 5. Extract text using OCR
                self.stdout.write("Extracting text with OCR...")
                raw_text = extract_text_from_pdf(pdf_path)

                # Clean up the temporary file
                os.remove(pdf_path)

                if not raw_text:
                    self.stderr.write(
                        self.style.ERROR(f"Failed to extract text from {url}")
                    )
                    continue

                # 6. Get structured data from LLM
                self.stdout.write("Sending text to LLM for structuring...")
                structured_info = get_structured_opportunity(raw_text)

                if not structured_info:
                    self.stderr.write(
                        self.style.ERROR(
                            f"Failed to get structured info from LLM for {url}"
                        )
                    )
                    continue

                # 7. Create the Post in the database
                self.stdout.write(f"Creating post: '{structured_info.title}'")

                new_post = Post.objects.create(
                    author=bot_user,
                    title=structured_info.title,
                    content=structured_info.summary,
                    source_url=url,
                )

                # Add the "opportunities" tag and other generated tags
                tags_to_add = ["opportunities"] + structured_info.tags
                for tag_name in tags_to_add:
                    tag, _ = Tag.objects.get_or_create(name=tag_name.lower().strip())
                    new_post.tags.add(tag)

                new_post.save()
                self.stdout.write(
                    self.style.SUCCESS(f"Successfully posted: {new_post.title}")
                )

            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(f"An error occurred while processing {url}: {e}")
                )

        self.stdout.write("Scholarship scraping process finished.")
