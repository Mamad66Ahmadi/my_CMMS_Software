document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("table.sortable th").forEach((header, columnIndex) => {
        if (header.classList.contains("no-sort")) return;

        header.style.cursor = "pointer";

        header.addEventListener("click", () => {
            const table = header.closest("table");
            const tbody = table.querySelector("tbody");
            const rows = Array.from(tbody.querySelectorAll("tr"));
            const asc = header.classList.toggle("asc");
            header.classList.toggle("desc", !asc);

            table.querySelectorAll("th").forEach(th => {
                if (th !== header) th.classList.remove("asc", "desc");
            });

            rows.sort((a, b) => {
                let A = a.children[columnIndex].innerText.trim();
                let B = b.children[columnIndex].innerText.trim();

                const numA = parseFloat(A.replace(/[^0-9.-]/g, ""));
                const numB = parseFloat(B.replace(/[^0-9.-]/g, ""));

                if (!isNaN(numA) && !isNaN(numB)) {
                    return asc ? numA - numB : numB - numA;
                }

                const dateA = Date.parse(A.replace(" ", "T"));
                const dateB = Date.parse(B.replace(" ", "T"));


                if (!isNaN(dateA) && !isNaN(dateB)) {
                    return asc ? dateA - dateB : dateB - dateA;
                }

                return asc
                    ? A.localeCompare(B)
                    : B.localeCompare(A);
            });

            rows.forEach(row => tbody.appendChild(row));
        });
    });
});
