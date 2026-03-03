// Progressive reveal animation
const revealTargets = Array.from(
    document.querySelectorAll(".reveal-up, .card, .tool-card, .featured-tile, .trend-item")
);

// Refresh-based aesthetic background palette
(() => {
    const palettes = [
        {
            base1: "#041424",
            base2: "#0f3d63",
            base3: "#072138",
            glow1: "rgba(80, 190, 255, 0.34)",
            glow2: "rgba(210, 242, 255, 0.22)",
        },
        {
            base1: "#0b1023",
            base2: "#243f7a",
            base3: "#101c3f",
            glow1: "rgba(120, 162, 255, 0.34)",
            glow2: "rgba(221, 232, 255, 0.22)",
        },
        {
            base1: "#1a0d1f",
            base2: "#5a1f62",
            base3: "#281333",
            glow1: "rgba(237, 129, 255, 0.32)",
            glow2: "rgba(251, 217, 255, 0.22)",
        },
        {
            base1: "#07161d",
            base2: "#16516a",
            base3: "#0b2733",
            glow1: "rgba(90, 220, 255, 0.3)",
            glow2: "rgba(212, 250, 255, 0.2)",
        },
        {
            base1: "#1b1107",
            base2: "#6b3d10",
            base3: "#2e1c0a",
            glow1: "rgba(255, 176, 89, 0.32)",
            glow2: "rgba(255, 232, 202, 0.22)",
        },
    ];
    const pick = palettes[Math.floor(Math.random() * palettes.length)];
    const root = document.documentElement;
    root.style.setProperty("--bg-base-1", pick.base1);
    root.style.setProperty("--bg-base-2", pick.base2);
    root.style.setProperty("--bg-base-3", pick.base3);
    root.style.setProperty("--bg-glow-1", pick.glow1);
    root.style.setProperty("--bg-glow-2", pick.glow2);
})();

if (revealTargets.length) {
    const revealObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.classList.add("in-view");
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.15 });

    revealTargets.forEach((item, index) => {
        if (!item.classList.contains("reveal-up")) item.classList.add("reveal-up");
        item.style.transitionDelay = `${Math.min(index * 0.03, 0.24)}s`;
        revealObserver.observe(item);
    });
}
// Toggle Password
function togglePassword() {
    const pass = document.getElementById("password");
    pass.type = pass.type === "password" ? "text" : "password";
}

// Form Validation
document.getElementById("signupForm")?.addEventListener("submit", function(e){
    e.preventDefault();

    let name = document.getElementById("name").value;
    let email = document.getElementById("email").value;
    let password = document.getElementById("password").value;

    if(name === "" || email === "" || password === ""){
        alert("Please fill all fields!");
        return;
    }

    if(password.length < 6){
        alert("Password must be at least 6 characters!");
        return;
    }

    alert("Account Created Successfully 🚀");
});// Auto image slider (one image at a time, swipe left every 5 sec by default)
document.querySelectorAll(".auto-slider-track").forEach((track) => {
    const slides = track.querySelectorAll(".auto-slide");
    if (!slides.length) return;

    let index = 0;
    const intervalMs = Number(track.dataset.interval || 5000);

    setInterval(() => {
        index = (index + 1) % slides.length;
        track.style.transform = `translateX(-${index * 100}%)`;
    }, intervalMs);
});

// Hide login status text after 5 seconds
const loginStatusToast = document.getElementById("login-status-toast");
if (loginStatusToast) {
    setTimeout(() => {
        loginStatusToast.classList.add("hide");
    }, 5000);
}

const siteCredit = document.querySelector(".site-credit");
if (siteCredit) {
    setTimeout(() => {
        siteCredit.classList.add("hide");
    }, 5000);
}

// Dashboard tool search
const toolSearch = document.getElementById("tool-search");
if (toolSearch) {
    const toolCards = Array.from(document.querySelectorAll("#tool-grid .tool-card"));
    const toolCount = document.getElementById("tool-count");
    const toolEmpty = document.getElementById("tool-empty-state");

    const updateTools = () => {
        const query = toolSearch.value.trim().toLowerCase();
        let visible = 0;

        toolCards.forEach((card) => {
            const text = (card.dataset.tool || card.textContent || "").toLowerCase();
            const match = !query || text.includes(query);
            card.hidden = !match;
            if (match) visible += 1;
        });

        if (toolCount) toolCount.textContent = `${visible} tool${visible === 1 ? "" : "s"}`;
        if (toolEmpty) toolEmpty.hidden = visible !== 0;
    };

    toolSearch.addEventListener("input", updateTools);
    updateTools();
}

// Global scroll animations (progress + subtle parallax)
const progressBar = document.createElement("div");
progressBar.className = "scroll-progress";
document.body.appendChild(progressBar);

const parallaxTargets = Array.from(
    document.querySelectorAll(
        ".hero-image-card img, .featured-tile img, .dashboard-gallery-card img, .image-grid img, .dashboard-hero-wrap, .feature-cta"
    )
);
parallaxTargets.forEach((el) => el.classList.add("parallax-item"));

let isTicking = false;
const onScrollAnimate = () => {
    const doc = document.documentElement;
    const maxScroll = Math.max(doc.scrollHeight - window.innerHeight, 1);
    const progress = Math.min((window.scrollY / maxScroll) * 100, 100);
    progressBar.style.width = `${progress}%`;

    parallaxTargets.forEach((el) => {
        const rect = el.getBoundingClientRect();
        if (rect.bottom < 0 || rect.top > window.innerHeight) return;
        const offsetFromCenter = rect.top + rect.height / 2 - window.innerHeight / 2;
        const speed = el.tagName === "IMG" ? 0.012 : 0.006;
        const moveY = Math.max(Math.min(-offsetFromCenter * speed, 14), -14);
        el.style.transform = `translate3d(0, ${moveY.toFixed(2)}px, 0)`;
    });
};

window.addEventListener("scroll", () => {
    if (isTicking) return;
    isTicking = true;
    window.requestAnimationFrame(() => {
        onScrollAnimate();
        isTicking = false;
    });
}, { passive: true });

window.addEventListener("resize", onScrollAnimate);
onScrollAnimate();

// Count-up stats (e.g., 1 -> 40K+) when section comes into view
const countUpItems = Array.from(document.querySelectorAll(".count-up[data-count-target]"));
if (countUpItems.length) {
    const animateCountUp = (el) => {
        const start = Number(el.dataset.countStart || 0);
        const target = Number(el.dataset.countTarget || 0);
        const duration = Number(el.dataset.countDuration || 1400);
        const prefix = el.dataset.countPrefix || "";
        const suffix = el.dataset.countSuffix || "";
        const decimals = Number(el.dataset.countDecimals || 0);
        let startTime = null;

        const render = (value) => {
            const valText = decimals > 0 ? value.toFixed(decimals) : String(Math.round(value));
            el.textContent = `${prefix}${valText}${suffix}`;
        };

        const tick = (timestamp) => {
            if (startTime === null) startTime = timestamp;
            const progress = Math.min((timestamp - startTime) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            const value = start + (target - start) * eased;
            render(value);

            if (progress < 1) {
                requestAnimationFrame(tick);
            } else {
                render(target);
                el.classList.add("count-done");
            }
        };

        requestAnimationFrame(tick);
    };

    const seen = new WeakSet();
    const counterObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach((entry) => {
            if (!entry.isIntersecting || seen.has(entry.target)) return;
            seen.add(entry.target);
            animateCountUp(entry.target);
            observer.unobserve(entry.target);
        });
    }, { threshold: 0.35 });

    countUpItems.forEach((item) => counterObserver.observe(item));
}

// Common-sense UX helpers
// 1) Trim common text fields on submit to avoid accidental blank-space inputs.
document.querySelectorAll("form").forEach((form) => {
    form.addEventListener("submit", () => {
        form.querySelectorAll("input[type='text'], input[type='email'], input[type='search'], textarea").forEach((el) => {
            if (typeof el.value === "string") el.value = el.value.trim();
        });
    });
});

// 2) Auto-resize textareas for easier writing.
document.querySelectorAll("textarea").forEach((ta) => {
    const resize = () => {
        ta.style.height = "auto";
        ta.style.height = `${Math.min(ta.scrollHeight, 240)}px`;
    };
    ta.addEventListener("input", resize);
    resize();
});

// 3) Smart navbar search: type intent, press Enter, jump to the relevant page.
const pageIntents = [
    { keys: ["home", "main", "landing"], path: "/" },
    { keys: ["feature", "tools", "capability"], path: "/features" },
    { keys: ["price", "pricing", "plan", "cost"], path: "/pricing" },
    { keys: ["about", "company"], path: "/about" },
    { keys: ["contact", "support", "help"], path: "/contact" },
    { keys: ["login", "sign in"], path: "/login" },
    { keys: ["signup", "sign up", "register", "create account"], path: "/signup" },
    { keys: ["start", "get started"], path: "/get-started" },
    { keys: ["dashboard", "workspace"], path: "/dashboard" },
    { keys: ["chat", "assistant", "ai"], path: "/ai/chat" },
];

document.querySelectorAll("nav.glass-nav .nav-search").forEach((searchBox) => {
    const searchInput = searchBox.querySelector("input");
    const searchBtn = searchBox.querySelector(".search-icon-btn");
    if (!searchInput) return;

    const runSearch = () => {
        const raw = (searchInput.value || "").trim().toLowerCase();
        if (!raw) return;

        if (raw.startsWith("/")) {
            window.location.href = raw;
            return;
        }

        const match = pageIntents.find((intent) => intent.keys.some((key) => raw.includes(key)));
        window.location.href = match ? match.path : "/get-started";
    };

    searchInput.addEventListener("keydown", (event) => {
        if (event.key !== "Enter") return;
        event.preventDefault();
        runSearch();
    });

    if (searchBtn) {
        searchBtn.addEventListener("click", runSearch);
    }
});

// Home hero rotating text (next enters from right, previous exits left)
const heroRotator = document.getElementById("hero-rotator-track");
if (heroRotator) {
    const items = Array.from(heroRotator.querySelectorAll(".hero-rotator-item"));
    let idx = items.findIndex((item) => item.classList.contains("active"));
    if (idx < 0) idx = 0;

    const rotate = () => {
        if (!items.length) return;
        const current = items[idx];
        const nextIndex = (idx + 1) % items.length;
        const next = items[nextIndex];

        current.classList.remove("active");
        current.classList.add("exit-left");
        next.classList.add("active");

        setTimeout(() => {
            current.classList.remove("exit-left");
        }, 700);

        idx = nextIndex;
    };

    setInterval(rotate, 2400);
}

// Sticky navbar style on scroll (always visible on both scroll directions)
const siteHeader = document.querySelector("header");
const updateHeaderState = () => {
    if (!siteHeader) return;
    siteHeader.classList.remove("nav-logo-only", "nav-hidden");

    if (window.scrollY <= 10 || window.innerWidth <= 768) {
        siteHeader.classList.remove("scrolled");
        return;
    }

    siteHeader.classList.add("scrolled");
};
window.addEventListener("scroll", updateHeaderState, { passive: true });
updateHeaderState();

// AI chat page interactions
const chatScroll = document.getElementById("chat-scroll");
if (chatScroll) {
    chatScroll.scrollTop = chatScroll.scrollHeight;
}

const chatForm = document.getElementById("ai-chat-form");
const chatInput = document.getElementById("chat-input");
if (chatForm && chatInput) {
    const sendBtn = chatForm.querySelector("button[type='submit']");

    document.querySelectorAll(".quick-prompt").forEach((btn) => {
        btn.addEventListener("click", () => {
            chatInput.value = btn.dataset.prompt || "";
            chatInput.focus();
        });
    });

    chatInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            chatForm.requestSubmit();
        }
    });

    chatForm.addEventListener("submit", () => {
        if (sendBtn) {
            sendBtn.disabled = true;
            sendBtn.textContent = "Sending...";
        }
    });
}

// Mobile menu toggle for all headers with nav links
document.querySelectorAll("header").forEach((header) => {
    const nav = header.querySelector("nav");
    if (!nav) return;
    const logo = header.querySelector(".logo");
    const navLogoLink = nav.querySelector(".nav-logo-link");

    if (navLogoLink && !header.querySelector(".mobile-header-brand")) {
        const mobileBrand = document.createElement("a");
        mobileBrand.className = "mobile-header-brand";
        mobileBrand.href = navLogoLink.getAttribute("href") || "/";
        mobileBrand.innerHTML = navLogoLink.innerHTML;
        header.insertBefore(mobileBrand, header.firstChild);
    }

    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "nav-toggle";
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-label", "Toggle menu");
    toggle.textContent = "☰";
    if (logo) {
        header.insertBefore(toggle, logo);
    } else {
        header.appendChild(toggle);
    }

    const closeMenu = () => {
        header.classList.remove("mobile-nav-open");
        toggle.setAttribute("aria-expanded", "false");
        toggle.textContent = "☰";
    };

    toggle.addEventListener("click", () => {
        const open = header.classList.toggle("mobile-nav-open");
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
        toggle.textContent = open ? "✕" : "☰";
    });

    nav.querySelectorAll("a").forEach((link) => {
        link.addEventListener("click", closeMenu);
    });

    window.addEventListener("resize", () => {
        if (window.innerWidth > 768) closeMenu();
    });
});
