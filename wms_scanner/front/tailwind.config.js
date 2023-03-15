/** @type {import('tailwindcss').Config} */ module.exports = {
  content: ["./**/*.{html,js}"],
  darkMode: "class", // or 'media' or 'class'
  theme: {
    fontFamily: {
      poppins: ["Poppins", "sans-serif"],
    },
    extend: {},
  },
  variants: {
    extend: {},
  },
  plugins: [],
};

// npx tailwindcss -i assets/css/dev.css -o assets/css/style.css -w 