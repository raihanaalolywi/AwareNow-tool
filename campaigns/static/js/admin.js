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
  
    document.querySelectorAll(".an-template-card").forEach(card => {
      card.addEventListener("click", () => {
        document.querySelectorAll(".an-template-card").forEach(c => c.classList.remove("is-selected"));
        card.classList.add("is-selected");
    
        const id = card.getAttribute("data-template-id");
        const input = document.getElementById("templateIdInput");
        if (input) input.value = id;
      });
    });    
  })();
