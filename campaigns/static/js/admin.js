(function () {
    // Shadow on scroll
    const nav = document.getElementById("anNavbar");
    if (nav) {
      const onScroll = () => {
        if (window.scrollY > 6) nav.classList.add("an-shadow");
        else nav.classList.remove("an-shadow");
      };
      window.addEventListener("scroll", onScroll, { passive: true });
      onScroll();
    }
  
    // Hover dropdown (Desktop only)
    const isDesktop = () => window.matchMedia("(min-width: 992px)").matches;
  
    document.querySelectorAll(".an-hover-dropdown").forEach((dd) => {
      const toggle = dd.querySelector('[data-bs-toggle="dropdown"]');
      if (!toggle) return;
  
      let bsDropdown = bootstrap.Dropdown.getOrCreateInstance(toggle);
  
      dd.addEventListener("mouseenter", () => {
        if (!isDesktop()) return;
        bsDropdown.show();
      });
  
      dd.addEventListener("mouseleave", () => {
        if (!isDesktop()) return;
        bsDropdown.hide();
      });
    });
  })();
  