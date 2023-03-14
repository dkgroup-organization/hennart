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

window.addEventListener('DOMContentLoaded', function() {
  document.querySelector("form input:first-child").focus()
});

// const emplacement = document.querySelector("#emplacement");

// emplacement.addEventListener("click", function () {
//   this.parentElement.classList.toggle("active");
// });

// document.addEventListener("click", function (event) {
//   if (!emplacement.contains(event.target)) {
//     emplacement.parentElement.classList.remove("active");
//   }
// });

// const buttons = document.querySelectorAll("#select-1 button");
// buttons.forEach(function (button) {
//   button.addEventListener("click", function (event) {
//     event.preventDefault();
//     const text = this.textContent.trim();
//     emplacement.setAttribute("value", text);
//   });
// });
