//Tab on dashboard
document.addEventListener("DOMContentLoaded", function () {
    const tabLinks = document.querySelectorAll(".tabs ul li a");
    const tabContents = document.querySelectorAll(".tab-content");

    function activateTab(tabId) {
      tabContents.forEach(content => {
        content.style.display = content.id === tabId ? "grid" : "none";
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


//transfer transaction
document.addEventListener("DOMContentLoaded", function () {
    const categorySelect = document.getElementById("id_category");
    const transferToField = document.getElementById("id_transfer_to");

    if (!categorySelect || !transferToField) return;

    // Wrap transfer_to field in a div if not already wrapped
    let wrapper = transferToField.closest('p');
    wrapper.id = "transfer-to-wrapper";

    function toggleTransferField() {
      const selectedOption = categorySelect.options[categorySelect.selectedIndex];
      const isTransfer = selectedOption?.text.toLowerCase().includes("transfer");
      wrapper.style.display = isTransfer ? "block" : "none";
    }

    categorySelect.addEventListener("change", toggleTransferField);
    toggleTransferField(); // Run on page load
  });

//account crypto
