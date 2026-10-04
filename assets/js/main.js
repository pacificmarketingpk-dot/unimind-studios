/* Unimind Studios — site behaviour. Everything works without this file; it only adds polish. */
(function () {
  "use strict";

  /* ---- Fill these in when you have them ---- */
  var doc = document.documentElement;
  // Values are written into <html data-...> by build.py from site.config.json
  var CONFIG = {
    bookingUrl: doc.getAttribute("data-booking") || "",
    formEndpoint: doc.getAttribute("data-endpoint") || "",
    contactPath: "contact/"
  };
  doc.classList.add("js");
  var root = doc.getAttribute("data-root") || "./";

  /* ---- Mega menu ---- */
  var megaBtn = document.querySelector("[data-mega-btn]");
  var mega = document.getElementById("mega");
  function setMega(open) {
    if (!megaBtn || !mega) return;
    megaBtn.setAttribute("aria-expanded", open ? "true" : "false");
    mega.classList.toggle("open", open);
  }
  if (megaBtn) {
    megaBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      setMega(megaBtn.getAttribute("aria-expanded") !== "true");
    });
    document.addEventListener("click", function (e) {
      if (mega && !mega.contains(e.target)) setMega(false);
    });
  }

  /* ---- Mobile menu ---- */
  var burger = document.querySelector("[data-burger]");
  var mobile = document.getElementById("mobile-menu");
  function setMobile(open) {
    if (!burger || !mobile) return;
    burger.setAttribute("aria-expanded", open ? "true" : "false");
    burger.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    mobile.classList.toggle("open", open);
    document.body.classList.toggle("lock", open);
    if (typeof onFloatScroll === "function") onFloatScroll();
  }
  if (burger) burger.addEventListener("click", function () {
    setMobile(burger.getAttribute("aria-expanded") !== "true");
  });
  if (mobile) mobile.addEventListener("click", function (e) {
    if (e.target.closest("a")) setMobile(false);
  });
  window.addEventListener("resize", function () {
    if (window.innerWidth > 1100) setMobile(false);
  });

  /* ---- Booking pop-up ---- */
  var modal = document.getElementById("booking");
  var lastFocus = null;
  var bookingLink = modal ? modal.querySelector("[data-booking-link]") : null;
  if (bookingLink) {
    if (CONFIG.bookingUrl) {
      bookingLink.href = CONFIG.bookingUrl;
      bookingLink.target = "_blank";
      bookingLink.rel = "noopener";
    } else {
      bookingLink.href = root + CONFIG.contactPath;
      bookingLink.textContent = "Send us a message instead";
    }
  }
  function openModal(e) {
    if (!modal) return;
    if (e) e.preventDefault();
    lastFocus = document.activeElement;
    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("lock");
    var c = modal.querySelector(".modal-close");
    if (c) c.focus();
  }
  function closeModal() {
    if (!modal) return;
    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
    if (!mobile || !mobile.classList.contains("open")) document.body.classList.remove("lock");
    if (lastFocus) lastFocus.focus();
    onFloatScroll();
  }
  document.addEventListener("click", function (e) {
    if (e.target.closest("[data-book]")) { setMobile(false); openModal(e); if (typeof setFloat === "function") setFloat(false); }
  });
  if (modal) {
    modal.addEventListener("click", function (e) {
      if (e.target.matches("[data-close]") || e.target.closest(".modal-close")) closeModal();
    });
    modal.addEventListener("keydown", function (e) {
      if (e.key !== "Tab") return;
      var f = modal.querySelectorAll("a[href],button:not([disabled])");
      var first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    });
  }
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    if (modal && modal.classList.contains("open")) closeModal();
    setMega(false);
    setMobile(false);
  });

  /* ---- Forms: validation, honeypot, messages ---- */
  var EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
  document.addEventListener("submit", function (e) {
    var form = e.target.closest("form[data-form]");
    if (!form) return;
    var msg = form.parentNode.querySelector(".form-msg");
    function say(text, ok) {
      if (!msg) return;
      msg.textContent = text;
      msg.className = "form-msg " + (ok ? "ok" : "err");
    }
    e.preventDefault();
    var bad = null;
    form.querySelectorAll("[required]").forEach(function (f) {
      var v = (f.value || "").trim();
      var okField = v && (f.type !== "email" || EMAIL.test(v));
      f.setAttribute("aria-invalid", okField ? "false" : "true");
      if (!okField && !bad) bad = f;
    });
    if (bad) {
      say(bad.type === "email" ? "Enter a full email address, like name@company.com." : "Fill in the highlighted field.", false);
      bad.focus();
      return;
    }
    var hp = form.querySelector(".hp input");
    if (hp && hp.value) { say(form.getAttribute("data-ok") || "Thanks.", true); form.reset(); return; }
    if (!CONFIG.formEndpoint) { say("This form isn't connected yet. Please email us instead.", false); return; }
    var btn = form.querySelector("button[type=submit]");
    if (btn) btn.disabled = true;
    fetch(CONFIG.formEndpoint, { method: "POST", body: new FormData(form), mode: "no-cors" })
      .then(function () { say(form.getAttribute("data-ok") || "Thanks. We'll be in touch.", true); form.reset(); })
      .catch(function () { say("That didn't send. Check your connection and try again.", false); })
      .then(function () { if (btn) btn.disabled = false; });
  });

  /* ---- Generic details pop-up (case studies, long quotes) ---- */
  var dlg = document.getElementById("dlg");
  var dlgBody = dlg ? dlg.querySelector(".dlg-body") : null;
  var dlgLast = null;
  function openDlg(src) {
    if (!dlg || !src) return;
    dlgLast = document.activeElement;
    dlgBody.innerHTML = src.innerHTML;
    dlg.classList.add("open");
    dlg.setAttribute("aria-hidden", "false");
    document.body.classList.add("lock");
    dlg.querySelector(".modal-close").focus();
  }
  function closeDlg() {
    if (!dlg || !dlg.classList.contains("open")) return;
    dlg.classList.remove("open");
    dlg.setAttribute("aria-hidden", "true");
    document.body.classList.remove("lock");
    dlgBody.innerHTML = "";
    if (dlgLast) dlgLast.focus();
    onFloatScroll();
  }
  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-open]");
    if (b) { e.preventDefault(); openDlg(document.getElementById(b.getAttribute("data-open"))); return; }
    if (dlg && (e.target.matches("#dlg [data-close]") || e.target.closest("#dlg .modal-close"))) closeDlg();
  });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeDlg(); });

  /* ---- Filters ---- */
  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-filter-group] .filters button");
    if (!b) return;
    var wrap = b.closest("[data-filter-group]");
    var f = b.getAttribute("data-f"), n = 0;
    wrap.querySelectorAll(".filters button").forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
    wrap.querySelectorAll("[data-cat]").forEach(function (it) {
      var show = f === "All" || it.getAttribute("data-cat") === f;
      it.hidden = !show; if (show) n++;
    });
    var count = wrap.querySelector(".count");
    if (count) count.textContent = n + " " + (n === 1 ? wrap.getAttribute("data-one") : wrap.getAttribute("data-many"));
  });

  /* ---- Pause buttons for moving rows ---- */
  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-pause]");
    if (!b) return;
    var target = document.getElementById(b.getAttribute("data-pause"));
    if (!target) return;
    var paused = target.classList.toggle("paused");
    b.setAttribute("aria-pressed", paused ? "true" : "false");
    b.textContent = paused ? "Play" : "Pause";
    var tr = target.querySelector(".marquee-track,.track");
    if (tr) tr.style.animationPlayState = paused ? "paused" : "";
  });

  /* ---- Gentle reveal ---- */
  var items = document.querySelectorAll(".reveal");
  var io = null;
  if ("IntersectionObserver" in window && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px" });
    items.forEach(function (el) { io.observe(el); });
  } else {
    items.forEach(function (el) { el.classList.add("in"); });
  }

  window.UnimindReveal = function (root) {
    (root || document).querySelectorAll(".reveal").forEach(function (el) {
      if (typeof io !== "undefined" && io) io.observe(el); else el.classList.add("in");
    });
  };

  /* ---- Floating "Book Meeting" bar ----
     Always visible once the visitor has scrolled past the page's hero section,
     in either direction. Hidden inside the hero (which has its own button)
     and while a pop-up or the mobile menu is open. */
  var fcta = document.getElementById("float-cta");
  var fbtn = fcta ? fcta.querySelector("a") : null;
  var fShown = false;
  function setFloat(show) {
    if (!fcta || show === fShown) return;
    fShown = show;
    fcta.classList.toggle("show", show);
    fcta.setAttribute("aria-hidden", show ? "false" : "true");
    if (fbtn) fbtn.tabIndex = show ? 0 : -1;
  }
  function onFloatScroll() {
    if (!fcta) return;
    var hero = document.querySelector("main .hero, main .pg-hero");
    var past = hero ? hero.getBoundingClientRect().bottom < 80 : window.scrollY > 400;
    setFloat(past && !document.body.classList.contains("lock"));
  }

  /* ---- Header gets solid when scrolled ---- */
  var ticking = false;
  function onScroll() { ticking = false; doc.classList.toggle("scrolled", window.scrollY > 20); onFloatScroll(); }
  window.addEventListener("scroll", function () { if (!ticking) { ticking = true; requestAnimationFrame(onScroll); } }, { passive: true });
  window.addEventListener("resize", onFloatScroll);
  window.addEventListener("hashchange", function () { setTimeout(onFloatScroll, 50); });
  onScroll();

  /* ---- Footer year ---- */
  var y = document.querySelector("[data-year]");
  if (y) y.textContent = new Date().getFullYear();
})();
