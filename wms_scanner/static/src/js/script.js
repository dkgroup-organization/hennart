const menuToggle = document.querySelector(".menu-toggle");
const header = document.querySelector("header");
const main = document.querySelector("main");
const body = document.querySelector("body");

menuToggle.addEventListener("click", function () {
  header.classList.toggle("menu-open");
  body.classList.toggle("bg-zinc-500");
  main.classList.toggle("z-[-1]");
  main.classList.toggle("brightness-50");
});
