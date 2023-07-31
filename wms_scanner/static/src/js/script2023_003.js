const menuToggle = document.querySelector(".menu-toggle");
const header = document.querySelector("header");
const main = document.querySelector("main");
const body = document.querySelector("body");
const popup = document.querySelector(".popup");
//const btn = document.querySelector(".next");
const closeBtn = document.querySelector(".popup .cursor-pointer");

menuToggle.addEventListener("click", function () {
  header.classList.toggle("menu-open");
  body.classList.toggle("bg-zinc-500");
  main.classList.toggle("z-[-1]");
  main.classList.toggle("brightness-50");
});

//btn.addEventListener("click", function (event) {
//  event.preventDefault();
//  popup.classList.add("flex");
//  popup.classList.remove("hidden");
//});

//closeBtn.addEventListener("click", function () {
//  popup.classList.add("hidden");
//});

function FocusScan() {
    var scan = document.getElementById("scan");

    if (scan != document.activeElement) {
        scan.focus();
        }
    }

document.addEventListener('keydown', FocusScan);
window.addEventListener('DOMContentLoaded', FocusScan);


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
