/** @odoo-module **/
import { registerPatch } from '@mail/model/model_core';
import { clear } from '@mail/model/model_field_command';
import Dialog from "web.Dialog";
const {_t} = require('web.core');
import '@mail/models/composer_view';
import { attr, many, one, enabled } from '@mail/model/model_field';
import { patch } from 'web.utils';

registerPatch({
    name: 'ComposerView',
    recordMethods: {
        onClickButtonMicrophone: function(ev){
          const self = this;
          var $this = $(ev.currentTarget);
          const searchFormInput = document.querySelector(".o_ComposerTextInput_textarea");
          const info = document.querySelector(".info");
          // The speech recognition interface lives on the browser’s window object
          const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition; // if none exists -> undefined
          console.log("SpeechRecognition", SpeechRecognition)
          if(SpeechRecognition) {
            console.log("Your Browser supports speech Recognition");
            const recognition = new SpeechRecognition();
            recognition.continuous = true;
            const micBtn = document.querySelector(".o_Composer_buttonMicrophone");
            const micIcon = micBtn.firstElementChild;
            micIcon.classList.remove("fa-microphone");
            micIcon.classList.add("fa-microphone-slash");
            recognition.start(); // First time you have to allow access to mic!
            function startSpeechRecognition() {
              searchFormInput.focus();
              console.log("Voice activated, SPEAK");
              if (info) {
                info.textContent = 'Start Recording';
              }
            }
            function endSpeechRecognition() {
              micIcon.classList.remove("fa-microphone-slash");
              micIcon.classList.add("fa-microphone");
              searchFormInput.focus();
              console.log("Speech recognition service disconnected");
              if (info) {
                info.textContent = ' ';
              }
            }
            function resultOfSpeechRecognition(event) {
                const current = event.resultIndex;
                const transcript = event.results[current][0].transcript;
                const sendButton = document.querySelector('.o_Composer_actionButton');
                if (transcript.toLowerCase().trim() === "stop recording") {
                    recognition.stop();
                } else if (!searchFormInput.value) {
                    searchFormInput.value = transcript;
                    sendButton.removeAttribute('disabled');
                    setTimeout(() => {
                        sendButton.click();
                        searchFormInput.click();
                    }, 2000)
                } else {
                    if (transcript.toLowerCase().trim() === "go") {
                        sendButton.click();
                        searchFormInput.click();
                    } else if (transcript.toLowerCase().trim() === "reset") {
                        searchFormInput.value = "";
                    } else {
                        searchFormInput.value = transcript;
                    }
                }
            }
            recognition.addEventListener("start", startSpeechRecognition.bind(this));
            recognition.addEventListener("end", endSpeechRecognition.bind(this));
            recognition.addEventListener("result", resultOfSpeechRecognition.bind(this));
          }
          else {
            console.log("Your Browser does not support speech Recognition");
            if (info) {
                info.textContent = "Your Browser does not support Speech Recognition";
            }
          }
        },
    }
});
