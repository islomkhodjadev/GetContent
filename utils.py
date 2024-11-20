import aiohttp
from bs4 import BeautifulSoup
import asyncpg
from dotenv import load_dotenv
import os
import asyncio

# Load environment variables
load_dotenv()


async def scrape_article_data(url):
    """
    Asynchronously scrape the title, categories, and content from a given article URL.

    Args
        url (str): The URL of the article to scrape.

    Returns:
        dict: A dictionary with the scraped title, categories, and content.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return {
                        "error": f"Failed to retrieve the webpage. Status code: {response.status}"
                    }
                html = await response.text()

        soup = BeautifulSoup(html, "html.parser")

        # Extract the title
        title_tag = soup.find("h1", class_="is-title post-title post-view-title")
        title = title_tag.get_text(strip=True) if title_tag else "No title found"

        # Extract categories
        category_div = soup.find("div", class_="post-meta-items meta-above")
        categories = (
            [a.get_text(strip=True) for a in category_div.find_all("a")]
            if category_div
            else ["No categories found"]
        )

        # Extract content
        content_div = soup.find(
            "div",
            class_="post-content post-content-custom cf entry-content content-spacious default__section border post-content-voice",
        )
        if content_div:
            paragraphs = content_div.find_all("p")
            full_content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            full_content = "No content found"

        return {
            "title": title,
            "categories": categories,
            "content": full_content,
        }

    except Exception as e:
        return {"error": f"An error occurred while scraping: {str(e)}"}


async def add_ai_data(heading, content, categories):
    """
    Asynchronously adds a record to the ai_data table and associates it with categories.

    Args:
        heading (str): The heading for the AI data.
        content (str): The content for the AI data.
        categories (list): A list of category names to associate with the data.

    Returns:
        str: Success message or error details.
    """
    try:
        # Connect to the PostgreSQL database
        connection = await asyncpg.connect(
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST", default="localhost"),
            port=os.getenv("DB_PORT", default="5432"),
        )

        # Insert data into the ai_data table
        ai_data_id = await connection.fetchval(
            "INSERT INTO api_aidata (heading, content) VALUES ($1, $2) RETURNING id",
            heading,
            content,
        )

        # Get category IDs for the provided category names
        existing_categories = await connection.fetch(
            "SELECT id, name FROM api_category WHERE name = ANY($1)", categories
        )
        existing_categories_dict = {
            row["name"]: row["id"] for row in existing_categories
        }

        # Insert any new categories into the category table
        new_categories = [
            cat for cat in categories if cat not in existing_categories_dict
        ]
        if new_categories:
            rows = await connection.fetch(
                "INSERT INTO api_category (name) VALUES ($1) ON CONFLICT (name) DO NOTHING RETURNING id, name",
                new_categories,
            )
            for row in rows:
                existing_categories_dict[row["name"]] = row["id"]

        # Create relationships in the ai_data_categories table
        category_ids = [existing_categories_dict[cat] for cat in categories]
        await connection.executemany(
            "INSERT INTO api_aidata_categories (aidata_id, category_id) VALUES ($1, $2)",
            [(ai_data_id, cat_id) for cat_id in category_ids],
        )

        return "Data successfully added to the database!"

    except Exception as e:
        return f"Error: {str(e)}"

    finally:
        await connection.close()
