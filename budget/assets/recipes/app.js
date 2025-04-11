// ------------------ Function Definitions ------------------

// Function to display scraped recipe
function displayScrapedRecipe(data) {
    // Display title
    document.getElementById('scraped-title').innerText = data.title || 'No title found';

    // Display ingredients
    const ingredientsList = document.getElementById('scraped-ingredients');
    ingredientsList.innerHTML = '';
    if (Array.isArray(data.ingredients)) {
        data.ingredients.forEach(ingredient => {
            const li = document.createElement('li');
            li.textContent = ingredient;
            ingredientsList.appendChild(li);
        });
    } else {
        ingredientsList.innerHTML = '<li>No ingredients found</li>';
    }

    // Display instructions
    const instructionsList = document.getElementById('scraped-instructions');
    instructionsList.innerHTML = '';
    let steps = data.instructions;
    if (typeof steps === 'string') {
        steps = steps.split('\n').map(step => step.trim()).filter(step => step.length > 0);
    }

    if (steps.length > 0) {
        steps.forEach(step => {
            const li = document.createElement('li');
            li.textContent = step;
            instructionsList.appendChild(li);
        });
    } else {
        instructionsList.innerHTML = '<li>No instructions found</li>';
    }

    // Display featured image
    const imageElement = document.getElementById('scraped-image');
    if (data.image && data.image !== 'No image found') {
        imageElement.src = data.image;
        imageElement.style.display = 'block';
        console.log(`Image displayed with src: ${data.image}`);
    } else {
        imageElement.style.display = 'none';
        console.log("No image found to display");
    }

    highlightNumbersInText('scraped-ingredients');
    highlightNumbersInText('scraped-instructions');
}

// Function to show save button
function showSaveButton(data) {
    const saveButton = document.getElementById('save-recipe');
    saveButton.style.display = 'block';

    saveButton.onclick = async function() {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        const instructions = Array.isArray(data.instructions) ? data.instructions.join('\n') : data.instructions;
        const originalUrl = data.original_url || "";
        const featuredImage = data.image || "";

        try {
            const response = await fetch('/recipes/save_recipe/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrfToken
                },
                body: `title=${encodeURIComponent(data.title)}&ingredients=${encodeURIComponent(data.ingredients.join('\n'))}&instructions=${encodeURIComponent(instructions)}&original_url=${encodeURIComponent(originalUrl)}&featured_image=${encodeURIComponent(featuredImage)}`
            });

            if (response.ok) {
                const result = await response.json();
                alert(result.message);
            } else {
                alert('Failed to save the recipe.');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred while saving the recipe.');
        }
    };
}

function highlightNumbersInText(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = element.innerHTML.replace(
            /(\b\d*(?:\s*[¼½¾⅓⅔⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞]|\s*\d+\/\d+)?(?:-\d+)?(?:°(?:[CF])?)?\s?(?:to|-)?\s?\d*(?:\s*[¼½¾⅓⅔⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞])?(?:\s*(?:g|gram[s]?|ml|oz|lb|kg|cup[s]?|tbsp|tablespoon[s]?|tsp|teaspoon[s]?|quart[s]?|minute[s]?|second[s]?|hour[s]?|°[CF]|\bdegree[s]?\s?(?:fahrenheit|celsius)?\b))\b)/gi,
            '<span class="highlight-number">$1</span>'
        );
    }
}

// ------------------ DOM Content Loaded ------------------

document.addEventListener('DOMContentLoaded', () => {
    // Modal elements
    const modal = document.getElementById('recipeModal');
    const openModalButton = document.getElementById('openModal');
    const closeModalButton = document.getElementById('closeModal');
    const urlModal = document.getElementById('urlModal');
    const closeUrlModalButton = document.getElementById('closeUrlModal');
    const createNewRecipeButton = document.getElementById('createNewRecipeButton');
    const enterUrlButton = document.getElementById('enterUrlButton');

    openModalButton?.addEventListener('click', () => modal.style.display = 'flex');
    closeModalButton?.addEventListener('click', () => modal.style.display = 'none');
    closeUrlModalButton?.addEventListener('click', () => urlModal.style.display = 'none');
    createNewRecipeButton?.addEventListener('click', () => window.location.href = '/add_recipe/');
    enterUrlButton?.addEventListener('click', () => window.location.href = '/recipes/scrape_recipes/');

    window.addEventListener('click', (event) => {
        if (event.target === urlModal) {
            urlModal.style.display = 'none';
        }
    });

    const scrapeForm = document.getElementById('scrape-form');
    if (scrapeForm) {
        scrapeForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            const url = document.getElementById('recipe-url').value;
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

            try {
                const response = await fetch('/recipes/scrape_recipe/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-CSRFToken': csrfToken
                    },
                    body: `url=${encodeURIComponent(url)}`
                });

                if (response.ok) {
                    const data = await response.json();
                    displayScrapedRecipe(data);
                    showSaveButton(data);
                } else {
                    alert('Failed to fetch recipe. Please check the URL.');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('An error occurred while fetching the recipe.');
            }
        });
    }

    // Nav toggle
    const navToggle = document.getElementById('navToggle');
    const sidebar = document.querySelector('.sidebar');
    navToggle?.addEventListener('click', () => sidebar.classList.toggle('active'));

    // Highlight numbers on page load
    highlightNumbersInText('scraped-ingredients');
    highlightNumbersInText('scraped-instructions');
});

// ------------------ Wake Lock ------------------

let wakeLock = null;
let wakeLockActive = false;

async function requestWakeLock() {
    try {
        wakeLock = await navigator.wakeLock.request('screen');
        wakeLockActive = true;
        updateWakeLockButton();
        wakeLock.addEventListener('release', () => {
            wakeLockActive = false;
            updateWakeLockButton();
        });
    } catch (err) {
        console.error(`${err.name}, ${err.message}`);
    }
}

function releaseWakeLock() {
    if (wakeLock !== null) {
        wakeLock.release().then(() => {
            wakeLock = null;
            wakeLockActive = false;
            updateWakeLockButton();
        });
    }
}

function toggleWakeLock() {
    if (wakeLockActive) {
        releaseWakeLock();
    } else {
        requestWakeLock();
    }
}

function updateWakeLockButton() {
    const wakeLockToggle = document.getElementById('wake-lock-toggle');
    wakeLockToggle.innerText = wakeLockActive ? 'Disable Screen Lock' : 'Keep Screen On';
}




