// ================= LOADER SYSTEM =================

document.addEventListener("DOMContentLoaded", function () {

    const loader = document.getElementById("loader");

    if (loader) {
        // Force remove loader after 1.2 seconds
        setTimeout(function () {
            loader.style.opacity = "0";
            loader.style.visibility = "hidden";

            setTimeout(function () {
                loader.style.display = "none";
            }, 600);

        }, 1200);
    }

});


// ================= FADE-IN ON SCROLL =================

document.addEventListener("DOMContentLoaded", function () {

    const elements = document.querySelectorAll(".fade-in");

    const observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add("show");
            }
        });
    }, {
        threshold: 0.2
    });

    elements.forEach(function (el) {
        observer.observe(el);
    });

});