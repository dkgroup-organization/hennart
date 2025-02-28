odoo.define('customize_account.dates', function(require) {
    "use strict";


    // Importation de la fonction originale à surcharger
    const { getPeriodOptions: originalGetPeriodOptions } = require('@web/search/utils/dates');

    console.log(originalGetPeriodOptions)

    // Définition de la nouvelle fonction getPeriodOptions
    function getPeriodOptions(referenceMoment) {
        // Appel à la fonction originale (optionnel, selon si tu veux l'utiliser)
        let periodOptions = originalGetPeriodOptions(referenceMoment);

        console.log(periodOptions)

        // Logique personnalisée pour modifier ou enrichir les options
        periodOptions = periodOptions.map(option => {
            // Exemple de modification : ajouter une description personnalisée
            option.description = `${option.description} (modifié)`;
            return option;
        });

        // Retourner les options modifiées
        return periodOptions;
    }

    // Exporter la fonction modifiée pour qu'elle remplace l'originale
    return {
        getPeriodOptions,
    };
});
