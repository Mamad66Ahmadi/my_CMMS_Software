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
            toggleBtn.classList.toggle("is-collapsed", collapsed);
            toggleBtn.setAttribute("aria-expanded", String(!collapsed));
            toggleBtn.setAttribute("aria-label", collapsed ? "Expand navigation" : "Collapse navigation");
            toggleBtn.title = collapsed ? "Expand navigation" : "Collapse navigation";
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
