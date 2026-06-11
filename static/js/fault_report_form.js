document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById("location-search-input");
    const resultsDiv = document.getElementById("location-results-container");
    const hiddenInput = document.getElementById("id_location_tag");
    const existingFaults = document.getElementById("existing-faults-container");

    // Stop if this page does not have the fault report location search elements
    if (!searchInput || !resultsDiv || !hiddenInput) {
        return;
    }

    let currentItems = [];
    let highlightedIndex = -1;

    function clearResults() {
        resultsDiv.innerHTML = "";
        currentItems = [];
        highlightedIndex = -1;
    }

    function updateHighlight() {
        const items = resultsDiv.querySelectorAll(".list-group-item-action");
        items.forEach((item, index) => {
            if (index === highlightedIndex) {
                item.classList.add("active");
            } else {
                item.classList.remove("active");
            }
        });
    }

    function renderResults(items) {
        clearResults();

        if (!items.length) {
            const noResult = document.createElement("div");
            noResult.className = "list-group-item disabled small text-muted";
            noResult.textContent = "No results found";
            resultsDiv.appendChild(noResult);
            return;
        }

        currentItems = items;

        items.forEach((item, index) => {
            const el = document.createElement("a");
            el.href = "#";
            el.className = "list-group-item list-group-item-action py-2 px-3 small";
            el.textContent = item.text;
            el.dataset.index = index;

            el.addEventListener("click", function (e) {
                e.preventDefault();
                selectItem(index);
            });

            resultsDiv.appendChild(el);
        });
    }

    function selectItem(index) {
        const item = currentItems[index];
        if (!item) return;

        searchInput.value = item.text;
        hiddenInput.value = item.id;

        clearResults();

        document.body.dispatchEvent(new Event("load-existing-faults"));
    }

    searchInput.addEventListener("input", function () {
        const query = this.value.trim();
        hiddenInput.value = "";
        highlightedIndex = -1;

        if (existingFaults) {
            existingFaults.innerHTML = "";
        }

        if (query.length < 2) {
            clearResults();
            return;
        }

        fetch(`${searchInput.dataset.autocompleteUrl}?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => renderResults(data.results || []))
            .catch(() => clearResults());
    });

    searchInput.addEventListener("keydown", function (e) {
        if (!currentItems.length) return;

        if (e.key === "ArrowDown") {
            e.preventDefault();
            highlightedIndex = (highlightedIndex + 1) % currentItems.length;
            updateHighlight();
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            highlightedIndex = (highlightedIndex - 1 + currentItems.length) % currentItems.length;
            updateHighlight();
        } else if (e.key === "Enter") {
            if (highlightedIndex >= 0) {
                e.preventDefault();
                selectItem(highlightedIndex);
            }
        } else if (e.key === "Escape") {
            clearResults();
        }
    });

    document.addEventListener("click", function (e) {
        if (!searchInput.contains(e.target) && !resultsDiv.contains(e.target)) {
            clearResults();
        }
    });

    // If editing/reviewing/converting an existing fault report that already has a location tag,
    // trigger HTMX to load possible duplicate faults immediately.
    if (hiddenInput.value) {
        document.body.dispatchEvent(new Event("load-existing-faults"));
    }
});
