function toggleProfileMenu(event) {
    event.stopPropagation();

    const menu = document.getElementById("profile-menu");
    const container = document.getElementById("profileContainer");

    if (!menu || !container) {
        return;
    }

    const isOpen = menu.style.display === "block";
    menu.style.display = isOpen ? "none" : "block";
    container.classList.toggle("open", !isOpen);
}

document.addEventListener("click", function (event) {
    const menu = document.getElementById("profile-menu");
    const container = document.getElementById("profileContainer");

    if (!menu || !container) {
        return;
    }

    if (!container.contains(event.target)) {
        menu.style.display = "none";
        container.classList.remove("open");
    }
});
