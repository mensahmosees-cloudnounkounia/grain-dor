/*
  reasoning-engine.js — Moteur de raisonnement Grain d'Or (version statique)

  Portage fidèle de raisonnement.py en JavaScript, pour que l'application
  puisse tourner sans aucun serveur (Render Static, GitHub Pages, ou
  simplement python -m http.server / Termux, qui ne font que servir des
  fichiers statiques, pas de code Python).

  Les formules et les seuils sont IDENTIQUES à raisonnement.py, testé et
  vérifié. Rien n'a été ajouté ni inventé ici.
*/

const SOLS = {
  argileux:        { label: "Argileux",        mult: 0.70, note: "Retient bien l'eau" },
  sableux:         { label: "Sableux",         mult: 1.25, note: "Draine vite, sèche fort" },
  limoneux:        { label: "Limoneux",        mult: 1.00, note: "Équilibré, idéal" },
  terre_de_barre:  { label: "Terre de barre",  mult: 0.85, note: "Plateau sud, ferralitique" },
  ferrugineux:     { label: "Ferrugineux",     mult: 1.10, note: "Nord, croûte en surface" },
  bas_fond:        { label: "Bas-fond",        mult: 0.55, note: "Zone humide, hydromorphe" },
  sablo_argileux:  { label: "Sablo-argileux",  mult: 0.95, note: "Mixte, bon compromis" },
  sol_noir:        { label: "Sol noir",        mult: 0.75, note: "Vertisol, craquelle au sec" },
  terre_rouge:     { label: "Terre rouge",     mult: 1.05, note: "Latérite, riche en fer" },
  terre_a_grain:   { label: "Terre à grain",   mult: 1.35, note: "Graveleuse, draine très vite" },
};

const PRIX_EAU_FCFA_L = 1.7;

function fmtFcfaEntier(n) {
  return Math.round(n).toLocaleString('fr-FR').replace(/\u00A0/g, ' ');
}

// ---------------------------------------------------------------------
// 1) Irrigation
// ---------------------------------------------------------------------
function conseilIrrigation(culture, sol, pluieMm, db) {
  const cultureData = db[culture];
  if (!cultureData) return { erreur: `Culture inconnue: ${culture}` };

  const solData = SOLS[sol] || SOLS.limoneux;
  const besoinBase = cultureData.eau_l_m2;

  if (pluieMm && pluieMm > 20) {
    const economie = Math.round(besoinBase * solData.mult * PRIX_EAU_FCFA_L * 10);
    return {
      action: "stop",
      message: `Pluie de ${pluieMm}mm prévue : pas besoin d'irriguer.`,
      economie_fcfa: economie,
      sol: solData.label,
    };
  }

  const dose = Math.round(besoinBase * solData.mult * 10) / 10;
  const cout = Math.round(dose * PRIX_EAU_FCFA_L);

  return {
    action: "irriguer",
    dose_litres_m2: dose,
    cout_fcfa: cout,
    sol: solData.label,
    conseil: cultureData.irrigation_conseil,
    message: `Irrigue ${dose} litres/m² pour ${culture}. Coût eau environ ${cout} F. Sol ${solData.label.toLowerCase()} (${solData.note.toLowerCase()}).`,
  };
}

// ---------------------------------------------------------------------
// 2) Calcul économique — gagner plus / dépenser moins
// ---------------------------------------------------------------------
function calculEconomique(culture, surfaceHa, db, coutIntrantsFcfa = 15000) {
  const cultureData = db[culture];
  if (!cultureData) return { erreur: `Culture inconnue: ${culture}` };

  const rendement = cultureData.rendement_kg_ha * surfaceHa;
  const prix = cultureData.prix_fcfa_kg;
  const revenuBrut = rendement * prix;
  const coutTotal = coutIntrantsFcfa * surfaceHa;
  const beneficeNet = revenuBrut - coutTotal;

  return {
    surface_ha: surfaceHa,
    rendement_kg: Math.round(rendement),
    revenu_brut_fcfa: Math.round(revenuBrut),
    cout_intrants_fcfa: Math.round(coutTotal),
    benefice_net_fcfa: Math.round(beneficeNet),
    message: `${culture} sur ${surfaceHa}ha : revenu brut ${fmtFcfaEntier(revenuBrut)}F, coûts ${fmtFcfaEntier(coutTotal)}F, bénéfice net ${fmtFcfaEntier(beneficeNet)}F.`,
  };
}

// ---------------------------------------------------------------------
// 3) Diagnostic ravageurs / maladies
// ---------------------------------------------------------------------
function diagnosticMaladie(culture, symptomeTexte, db) {
  const cultureData = db[culture];
  if (!cultureData) return { erreur: `Culture inconnue: ${culture}` };

  const texte = (symptomeTexte || "").toLowerCase().trim();
  if (!texte) {
    return {
      trouve: false,
      message: `Décris le symptôme sur ${culture} (ex: feuille jaune, trou, chenille, pourri).`,
    };
  }

  for (const ravageur of (cultureData.ravageurs || [])) {
    for (const cle of ravageur.cles) {
      if (texte.includes(cle)) {
        const coutFmt = fmtFcfaEntier(ravageur.cout_evite);
        const resultat = {
          trouve: true,
          nom: ravageur.nom,
          traitement: ravageur.traitement,
          cout_evite_fcfa: ravageur.cout_evite,
          message: `${ravageur.nom} probable sur ${culture}. ${ravageur.traitement}. Économie estimée ${coutFmt}F vs traitement chimique systématique.`,
        };
        if (ravageur.savoir_paysan) {
          resultat.savoir_paysan = ravageur.savoir_paysan;
          resultat.savoir_paysan_note = ravageur.savoir_paysan_note || "";
          resultat.savoir_paysan_source = ravageur.savoir_paysan_source || "";
        }
        return resultat;
      }
    }
  }

  return {
    trouve: false,
    message: `Symptôme non reconnu pour ${culture}. Surveille 2 jours, prends une photo, évite un traitement chimique systématique tant que le doute n'est pas levé.`,
  };
}

// ---------------------------------------------------------------------
// 4) Calendrier cultural
// ---------------------------------------------------------------------
function addDays(date, days) {
  const d = new Date(date);
  d.setDate(d.getDate() + days);
  return d;
}
function isoDate(d) {
  return d.toISOString().slice(0, 10);
}
function frDate(d) {
  return d.toLocaleDateString('fr-FR', { year: 'numeric', month: '2-digit', day: '2-digit' });
}

function calendrier(culture, db, dateDepart) {
  const cultureData = db[culture];
  if (!cultureData) return { erreur: `Culture inconnue: ${culture}` };

  const depart = dateDepart || new Date();
  const fertilisation = addDays(depart, 30);
  const traitementPrevention = addDays(depart, 45);
  const recolte = addDays(depart, cultureData.cycle_jours);

  return {
    semis_periode: cultureData.semis,
    date_fertilisation: isoDate(fertilisation),
    engrais: cultureData.engrais,
    date_traitement_preventif: isoDate(traitementPrevention),
    date_recolte_estimee: isoDate(recolte),
    cycle_jours: cultureData.cycle_jours,
    message: `${culture} : semis ${cultureData.semis} · fertilisation le ${isoDate(fertilisation)} (${cultureData.engrais}) · récolte estimée le ${isoDate(recolte)} (dans ${cultureData.cycle_jours}j).`,
  };
}

// ---------------------------------------------------------------------
// 5) Analyse de sol
// ---------------------------------------------------------------------
function analyseSol(culture, pH, humiditePct, fertilite, db) {
  const cultureData = db[culture] || {};
  const conseils = [];

  let ph = parseFloat(pH);
  if (isNaN(ph)) ph = 6.0;
  let humidite = parseFloat(humiditePct);
  if (isNaN(humidite)) humidite = 50.0;

  const phMin = cultureData.ph_min ?? 5.5;
  const phMax = cultureData.ph_max ?? 7.0;

  if (ph < phMin) {
    conseils.push("pH trop acide pour cette culture : ajoute cendre de bois (500kg/ha) ou chaux agricole.");
  } else if (ph > phMax) {
    conseils.push("pH trop basique pour cette culture : ajoute compost acide ou fumier bien décomposé.");
  } else {
    conseils.push("pH dans la bonne fourchette pour cette culture.");
  }

  if (humidite < 30) {
    conseils.push("Sol sec : paillage conseillé + arrosage léger d'appoint.");
  } else if (humidite > 80) {
    conseils.push("Sol très humide : vérifie le drainage pour éviter la pourriture des racines.");
  }

  if (fertilite === "faible") {
    conseils.push("Fertilité faible : 5T de compost/ha + rotation avec une légumineuse (niébé, soja).");
  }

  conseils.push("Enregistre ces mesures (traçabilité) : jusqu'à +15% de valeur à la vente.");

  return { pH: ph, humidite_pct: humidite, conseils, message: conseils.join(" ") };
}

// ---------------------------------------------------------------------
// 6) Gestion du risque météo
// ---------------------------------------------------------------------
function gestionRisque(culture, pluiePrevueMm, ventFort = false) {
  const alertes = [];
  let niveau = "faible";

  if (pluiePrevueMm && pluiePrevueMm > 40) {
    niveau = "élevé";
    alertes.push("Pluie forte prévue (>40mm) : creuse des rigoles d'évacuation avant la pluie.");
  } else if (pluiePrevueMm && pluiePrevueMm > 20) {
    niveau = "modéré";
    alertes.push("Pluie significative prévue : pas besoin d'irriguer, surveille le drainage.");
  }

  if (ventFort) {
    if (niveau !== "élevé") niveau = "élevé";
    alertes.push(`Vent violent annoncé : tuteure les plants de ${culture} sensibles à la casse.`);
  }

  if (alertes.length === 0) {
    alertes.push("Aucun risque météo majeur signalé pour le moment.");
  }

  return { niveau, alertes, message: alertes.join(" ") };
}

// ---------------------------------------------------------------------
// 7) Détection d'émotion simple
// ---------------------------------------------------------------------
const EMOTIONS = {
  content:  ["😊💪", "Tu es content, c'est mérité !"],
  triste:   ["😢🌱", "Je comprends, la terre est parfois dure. On avance ensemble."],
  fier:     ["😎🔥", "Bravo, continue comme ça !"],
  inquiet:  ["😰🌧️", "Pas de panique, on regarde la situation ensemble."],
  neutre:   ["🤔🌾", "Je t'écoute, parlons de ton champ."],
};
const MOTS_CONTENT = ["merci", "content", "bien", "fort"];
const MOTS_TRISTE  = ["perdu", "triste", "mort", "malade", "peur"];
const MOTS_FIER    = ["réussi", "reussi", "gagné", "gagne"];
const MOTS_INQUIET = ["pluie", "sécheresse", "secheresse", "vent", "inquiet"];

function detecterEmotion(texte) {
  const t = (texte || "").toLowerCase();
  let cle = "neutre";
  if (MOTS_CONTENT.some(m => t.includes(m))) cle = "content";
  else if (MOTS_TRISTE.some(m => t.includes(m))) cle = "triste";
  else if (MOTS_FIER.some(m => t.includes(m))) cle = "fier";
  else if (MOTS_INQUIET.some(m => t.includes(m))) cle = "inquiet";
  const [emoji, message] = EMOTIONS[cle];
  return { emotion: cle, emoji, message };
}

// ---------------------------------------------------------------------
// 8) Raisonnement complet — équivalent exact de raisonner() en Python
// ---------------------------------------------------------------------
function raisonner({ culture, sol, pluie_mm, surface_ha = 1.0, pH, humidite_pct,
                      fertilite = "moyenne", symptome_texte = "", texte_utilisateur = "" }, db) {
  return {
    "1_intention": { culture, sol: (SOLS[sol] && SOLS[sol].label) || sol },
    "2_contexte": analyseSol(culture, pH, humidite_pct, fertilite, db),
    "3_economie": {
      irrigation: conseilIrrigation(culture, sol, pluie_mm, db),
      benefice: calculEconomique(culture, surface_ha, db),
    },
    "4_risque": {
      meteo: gestionRisque(culture, pluie_mm),
      diagnostic: symptome_texte ? diagnosticMaladie(culture, symptome_texte, db) : null,
    },
    "5_plan": calendrier(culture, db),
    emotion: texte_utilisateur ? detecterEmotion(texte_utilisateur) : null,
  };
}

// Exposé pour usage dans frontend.html (script classique, pas de modules)
window.GrainDorEngine = {
  SOLS, raisonner, conseilIrrigation, calculEconomique, diagnosticMaladie,
  calendrier, analyseSol, gestionRisque, detecterEmotion,
};
