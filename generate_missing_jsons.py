import json
import os

topics = {
    "model": {
        "topic": "model",
        "label": "Création de Modèle Odoo",
        "imports": "from odoo import models, fields, api",
        "snippet": "class CustomModel(models.Model):\n    _name = 'custom.model'\n    _description = 'Description du modèle'\n\n    name = fields.Char(string='Nom', required=True)\n    active = fields.Boolean(default=True)\n    state = fields.Selection([('draft', 'Brouillon'), ('done', 'Terminé')], default='draft')\n",
        "rules": [
            "Toujours définir _name et _description.",
            "Utiliser les types de champs standards (Char, Boolean, Selection, Many2one, etc.).",
            "Pour les champs relationnels (Many2one, One2many, Many2many), toujours spécifier le comodel_name."
        ],
        "anti_patterns": [
            "❌ Oublier _description (provoque un warning dans les logs).",
            "❌ Utiliser des mots réservés SQL comme noms de champs (ex: 'order', 'select')."
        ],
        "related_topics": ["compute_field", "constraint", "onchange"],
        "difficulty": "beginner"
    },
    "action_menu": {
        "topic": "action_menu",
        "label": "Actions et Menus (ir.actions & menuitem)",
        "imports": "",
        "snippet": "<record id=\"action_custom_model\" model=\"ir.actions.act_window\">\n    <field name=\"name\">Modèles Personnalisés</field>\n    <field name=\"res_model\">custom.model</field>\n    <field name=\"view_mode\">tree,form</field>\n</record>\n\n<menuitem id=\"menu_custom_root\" name=\"Application Personnalisée\" sequence=\"10\"/>\n<menuitem id=\"menu_custom_model\" name=\"Modèles\" parent=\"menu_custom_root\" action=\"action_custom_model\" sequence=\"10\"/>\n",
        "rules": [
            "Toujours définir view_mode avec au moins tree,form.",
            "Lier l'action au menuitem via l'attribut 'action'.",
            "Utiliser des IDs uniques et descriptifs."
        ],
        "anti_patterns": [
            "❌ Mettre un parent inexistant pour un menuitem.",
            "❌ Oublier de déclarer le fichier XML dans __manifest__.py."
        ],
        "related_topics": ["view_tree", "view_form"],
        "difficulty": "beginner"
    },
    "cron": {
        "topic": "cron",
        "label": "Tâches Planifiées (ir.cron)",
        "imports": "",
        "snippet": "<record id=\"ir_cron_custom_task\" model=\"ir.cron\">\n    <field name=\"name\">Tâche Planifiée Personnalisée</field>\n    <field name=\"model_id\" ref=\"model_custom_model\"/>\n    <field name=\"state\">code</field>\n    <field name=\"code\">model._cron_custom_task()</field>\n    <field name=\"interval_number\">1</field>\n    <field name=\"interval_type\">days</field>\n    <field name=\"numbercall\">-1</field>\n    <field name=\"active\" eval=\"True\"/>\n</record>\n",
        "rules": [
            "La méthode appelée (définie dans 'code') doit être décorée avec @api.model.",
            "Toujours utiliser ref=\"model_nom_du_modele_avec_underscores\" pour le model_id.",
            "Gérer les gros volumes de données par lots (batching) pour éviter les timeouts."
        ],
        "anti_patterns": [
            "❌ Faire un cron qui tourne trop souvent (ex: chaque minute) pour des tâches lourdes.",
            "❌ Appeler des méthodes qui nécessitent l'interface utilisateur ou `self.env.user`."
        ],
        "related_topics": ["model"],
        "difficulty": "intermediate"
    },
    "owl": {
        "topic": "owl",
        "label": "Composants OWL",
        "imports": "import { Component, useState } from \"@odoo/owl\";\nimport { registry } from \"@web/core/registry\";",
        "snippet": "export class CustomComponent extends Component {\n    static template = \"mon_module.CustomTemplate\";\n    \n    setup() {\n        this.state = useState({ count: 0 });\n    }\n    \n    increment() {\n        this.state.count++;\n    }\n}\n\nregistry.category(\"actions\").add(\"custom_action_tag\", CustomComponent);\n",
        "rules": [
            "Toujours hériter de `Component` provenant de `@odoo/owl`.",
            "Utiliser `useState` pour les données réactives.",
            "Enregistrer le composant dans la bonne catégorie du registre (actions, fields, views...)."
        ],
        "anti_patterns": [
            "❌ Manipuler directement le DOM avec `document.getElementById`.",
            "❌ Oublier de définir le `static template` ou de l'ajouter dans les assets."
        ],
        "related_topics": [],
        "difficulty": "advanced"
    }
}

base_path = "c:/DTOPrompt/knowledge"
versions = ["17", "18", "19"]

for v in versions:
    for topic_name, data in topics.items():
        data_copy = data.copy()
        data_copy["version"] = v
        
        # Ajout de spécificités pour la version
        if topic_name == "owl":
            if v == "17":
                data_copy["rules"].append("Odoo 17 utilise OWL 2. Assurez-vous d'utiliser la syntaxe moderne.")
            elif v in ["18", "19"]:
                data_copy["rules"].append(f"Odoo {v} : Utiliser les hooks standards @web/core/utils/hooks.")
                
        file_path = os.path.join(base_path, f"v{v}", f"{topic_name}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data_copy, f, indent=4, ensure_ascii=False)
            print(f"Created {file_path}")
