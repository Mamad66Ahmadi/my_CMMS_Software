(function () {
    function initializeSidebar() {
        const sidebar = document.getElementById("sidebar");
        const toggleBtn = document.getElementById("sidebarToggle");

        if (!sidebar || !toggleBtn) {
            return;
        }

        function applyState(collapsed) {
            sidebar.classList.toggle("collapsed", collapsed);
            document.body.classList.toggle("sidebar-collapsed", collapsed);
            toggleBtn.innerHTML = collapsed ? "&#8250;" : "&#8249;";
        }

        applyState(localStorage.getItem("sidebarCollapsed") === "true");

        toggleBtn.addEventListener("click", function () {
            const collapsed = !sidebar.classList.contains("collapsed");
            applyState(collapsed);
            localStorage.setItem("sidebarCollapsed", collapsed);
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initializeSidebar);
    } else {
        initializeSidebar();
    }
})();
