# -*- coding: utf-8 -*-
#################################################################################
# Author      : PIT Solutions AG. (<https://www.pitsolutions.ch/>)
# Copyright(c): 2019 - Present PIT Solutions AG.
# License URL : https://www.webshopextension.com/en/licence-agreement/
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://www.webshopextension.com/en/licence-agreement/>
#################################################################################

{
    "name": "Voice to Text Chatter",
    "version": "16.0.1.0.0",
    "summary": "Voice to Text Chatter",
    "description": "Voice to Text Chatter helps you to convert your voice to text and sends the messages.",
    "license": "OPL-1",
    "author": "PIT Solutions AG",
    "live_test_url": "http://saas.dev.displayme.net/demo-register/?technical_name=pits_voice_to_text_chatter&version=16.0&access_key=ZcE-49Z-Mri",
    "depends": ["mail", "web", ],
    "data": [
    ],
    "demo": [],
    "assets": {
        'mail.assets_core_messaging': [
            'pits_voice_to_text_chatter/static/src/js/speech.js',
        ],
        'web.assets_backend': [
            'pits_voice_to_text_chatter/static/src/components/*/*.xml',
        ],
    },
    "images": ["static/description/banner.png"],
    'installable': True,
    'application': False,
    'auto_install': False,
}
