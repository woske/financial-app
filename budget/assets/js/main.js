
document.addEventListener("DOMContentLoaded", function () {
const tabLinks = document.querySelectorAll(".tabs ul li a");
const tabContents = document.querySelectorAll(".tab-content");

function activateTab(tabId) {
    tabContents.forEach(content => {
    content.style.display = content.id === tabId ? "block" : "none";
    });

    tabLinks.forEach(link => {
    link.parentElement.classList.toggle("active", link.getAttribute("href").substring(1) === tabId);
    });
}

tabLinks.forEach(link => {
    link.addEventListener("click", function (e) {
    e.preventDefault();
    const tabId = this.getAttribute("href").substring(1);
    activateTab(tabId);
    });
});

// Activate first tab by default
if (tabLinks.length > 0) {
    activateTab(tabLinks[0].getAttribute("href").substring(1));
}
});

