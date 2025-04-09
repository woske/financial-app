import json
from bs4 import BeautifulSoup

class CustomScraper:
    def __init__(self, content, url):
        self.soup = BeautifulSoup(content, 'html.parser')
        self.url = url

    def title(self):
        title = self._get_json_ld_title() or self.soup.find('title')
        return title.text.strip() if title else 'No title found'

    def ingredients(self):
        ingredients = self._get_json_ld_ingredients() or self._get_focused_html_ingredients()
        return ingredients if ingredients else ['No ingredients found']

    def instructions(self):
        instructions = self._get_json_ld_instructions() or self._get_focused_html_instructions()
        return instructions if instructions else ['No instructions found']

    def featured_image(self):
        # 1. Try to get the image from JSON-LD structured data
        image = self._get_json_ld_image()
        if image:
            return image

        # 2. Check for an image in the "og:image" meta tag
        og_image = self.soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            return og_image['content']

        # 3. Check for an image within a div with class "tasty-recipes-image" or similar
        image_container = self.soup.find('div', class_='tasty-recipes-image')
        if image_container:
            img_tag = image_container.find('img')
            if img_tag and img_tag.get('src'):
                return img_tag['src']

        # 4. Try finding the first <img> tag with common class names related to recipes
        img_tag = self.soup.find('img', class_=['featured', 'thumbnail', 'wprm-recipe-image', 'recipe-image'])
        if img_tag and img_tag.get('src'):
            return img_tag['src']

        # 5. As a last resort, try the first <img> tag on the page
        first_img = self.soup.find('img')
        if first_img and first_img.get('src'):
            return first_img['src']

        return 'No image found'

    def _get_json_ld_title(self):
        json_ld_data = self._get_json_ld_data()
        if json_ld_data:
            return json_ld_data.get('name')

    def _get_json_ld_ingredients(self):
        json_ld_data = self._get_json_ld_data()
        if json_ld_data:
            return json_ld_data.get('recipeIngredient')

    def _get_json_ld_instructions(self):
        json_ld_data = self._get_json_ld_data()
        if json_ld_data:
            instructions = json_ld_data.get('recipeInstructions')
            if isinstance(instructions, list):
                return [step['text'] for step in instructions if isinstance(step, dict) and 'text' in step]
            elif isinstance(instructions, str):
                return instructions.split('. ')

    def _get_json_ld_image(self):
        # Extract the image from JSON-LD structured data
        json_ld_data = self._get_json_ld_data()
        if json_ld_data:
            return json_ld_data.get('image')

    def _get_json_ld_data(self):
        json_ld = self.soup.find('script', type='application/ld+json')
        if json_ld:
            try:
                data = json.loads(json_ld.string)
                if isinstance(data, list):
                    for item in data:
                        if item.get('@type') == 'Recipe':
                            return item
                elif data.get('@type') == 'Recipe':
                    return data
            except json.JSONDecodeError:
                pass
        return None

    def _get_focused_html_ingredients(self):
        ingredients = []
        seen_ingredients = set()

        ingredient_container = self.soup.select_one('[class*="ingredient"], [class*="wprm-recipe-ingredient"], [class*="tasty-recipes-ingredient"], .ingredients')
        if ingredient_container:
            list_items = ingredient_container.find_all(['li', 'p'])  # Look for both <li> and <p> tags

            if not list_items:
                # Use separator=', ' to ensure spaces between words are maintained
                text = ingredient_container.get_text(separator=', ', strip=True)
                split_ingredients = text.split(',')
                for ingredient in split_ingredients:
                    ingredient = ingredient.strip()
                    if ingredient and ingredient.lower() not in seen_ingredients and not any(keyword in ingredient.lower() for keyword in ['scale', 'ingredient']):
                        ingredients.append(ingredient)
                        seen_ingredients.add(ingredient.lower())
            else:
                for item in list_items:
                    # Use separator=' ' to ensure spaces between words are maintained
                    text = item.get_text(separator=' ', strip=True)
                    if text and text.lower() not in seen_ingredients:
                        ingredients.append(text)
                        seen_ingredients.add(text.lower())

        return ingredients

    def _get_focused_html_instructions(self):
        instructions = []
        seen_instructions = set()

        # Primary instruction container search
        instruction_container = self.soup.select_one('[class*="instruction"], [class*="wprm-recipe-instruction"], [class*="tasty-recipe-instructions"], .instructions, .steps')
        if instruction_container:
            list_items = instruction_container.find_all(['li', 'p'])  # Look for both <li> and <p> tags

            if not list_items:
                # Use separator='. ' to ensure spaces between sentences are maintained
                text = instruction_container.get_text(separator='. ', strip=True)
                split_instructions = text.split('. ')
                for instruction in split_instructions:
                    instruction = instruction.strip()
                    if instruction and instruction.lower() not in seen_instructions and not any(keyword in instruction.lower() for keyword in ['instructions']):
                        instructions.append(instruction)
                        seen_instructions.add(instruction.lower())
            else:
                for item in list_items:
                    # Use separator=' ' to ensure spaces between words are maintained
                    text = item.get_text(separator=' ', strip=True)
                    if text and text.lower() not in seen_instructions:
                        instructions.append(text)
                        seen_instructions.add(text.lower())

        # Fallback to a more general search if no instructions were found
        if not instructions:
            all_paragraphs = self.soup.find_all('p')
            for p in all_paragraphs:
                text = p.get_text(separator=' ', strip=True)
                if "step" in text.lower() or "instruction" in text.lower() or "prepare" in text.lower():
                    if text and text.lower() not in seen_instructions:
                        instructions.append(text)
                        seen_instructions.add(text.lower())

        return instructions
