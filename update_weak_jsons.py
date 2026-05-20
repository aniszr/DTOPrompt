import json
import os

base_path = "c:/DTOPrompt/knowledge"

# Data for v19 weak files
v19_files = {
    "inheritance": {
        "version": "19",
        "topic": "inheritance",
        "label": "Héritage Odoo 19 (_inherit & _inherits)",
        "imports": "from odoo import api, fields, models",
        "snippet": "class ResPartnerInherit(models.Model):\n    _inherit = 'res.partner'\n\n    custom_score = fields.Integer(string=\"Score\")\n\n# Héritage par délégation\nclass CustomUser(models.Model):\n    _name = 'custom.user'\n    _inherits = {'res.users': 'user_id'}\n    user_id = fields.Many2one('res.users', required=True, ondelete='cascade')\n\n<record id=\"view_partner_form_inherit\" model=\"ir.ui.view\">\n    <field name=\"name\">res.partner.form.inherit</field>\n    <field name=\"model\">res.partner</field>\n    <field name=\"inherit_id\" ref=\"base.view_partner_form\"/>\n    <field name=\"arch\" type=\"xml\">\n        <xpath expr=\"//field[@name='vat']\" position=\"after\">\n            <field name=\"custom_score\" invisible=\"not is_company\"/>\n        </xpath>\n    </field>\n</record>",
        "rules": [
            "L'héritage classique (_inherit) modifie le modèle en place, sans créer de nouvelle table",
            "L'héritage par délégation (_inherits) lie un modèle parent via un champ Many2one, fusionnant les champs dans l'interface",
            "En XML, les attributs dynamiques (invisible, readonly) s'écrivent avec l'évaluation Python directe depuis Odoo 17+",
            "Éviter xpath position=\"replace\", préférer invisibiliser le champ",
            "Préciser toujours l'inherit_id avec module.xml_id dans les vues",
            "Lors de l'héritage de fonctions Python, utiliser super() pour appeler la méthode d'origine"
        ],
        "anti_patterns": [
            "❌ attrs={'invisible': [('is_company','=',False)]} — l'attribut attrs n'existe plus en Odoo 17+",
            "❌ Remplacer des blocs entiers de vue avec xpath expr='//sheet' position='replace'",
            "❌ Oublier ondelete='cascade' sur le Many2one dans un héritage _inherits",
            "❌ Oublier de retourner le résultat de super() dans une méthode héritée"
        ],
        "advanced": {
            "delegation": {
                "trigger_keywords": ["délégation", "inherits", "héritage par délégation"],
                "snippet": "_inherits = {'res.partner': 'partner_id'}",
                "warning": "La délégation implique que chaque enregistrement créé créera aussi un enregistrement du modèle parent."
            }
        },
        "related_topics": ["view_form"],
        "difficulty": "beginner",
        "last_updated": "2026-05-19"
    },
    "controller": {
        "version": "19",
        "topic": "controller",
        "label": "Routes HTTP & JSON (Controllers) Odoo 19",
        "imports": "from odoo import http\nfrom odoo.http import request",
        "snippet": "class CustomController(http.Controller):\n\n    @http.route('/my_route/hello', type='http', auth='public', website=True)\n    def hello_world(self, **kwargs):\n        return request.render('my_module.template_hello', {})\n\n    @http.route('/api/custom/data', type='json', auth='user', methods=['POST'])\n    def get_custom_data(self, **post):\n        records = request.env['custom.model'].search([])\n        return {'status': 'success', 'data': records.read(['name'])}\n",
        "rules": [
            "type='http' retourne du texte HTML ou une requête de rendu QWeb",
            "type='json' retourne automatiquement du JSON, utilisé pour les appels RPC Odoo",
            "auth='public' pour les visiteurs anonymes, auth='user' pour les utilisateurs connectés",
            "Utiliser request.env pour accéder à l'ORM à l'intérieur du contrôleur",
            "Le paramètre website=True active le contexte website pour le routage",
            "En Odoo 19, valider toujours les entrées utilisateurs avec `kwargs` ou `post`",
            "Gérer les exceptions avec werkzeug.exceptions si la route retourne une erreur HTTP"
        ],
        "anti_patterns": [
            "❌ Retourner une string brute en JSON (Odoo s'occupe de la sérialisation si type='json')",
            "❌ Oublier l'attribut auth — défaut est auth='user', ce qui bloquera les appels publics",
            "❌ Exécuter des requêtes lourdes non limitées sans pagination",
            "❌ Mettre des opérations CRUD directement dans des requêtes GET (limiter les modifications aux méthodes POST)"
        ],
        "advanced": {
            "cors": {
                "trigger_keywords": ["cors", "cross origin", "externe", "api externe"],
                "snippet": "@http.route('/api', type='json', auth='none', cors='*')",
                "warning": "Gérer la sécurité : cors='*' expose l'API publiquement. auth='none' n'initialise pas de base de données."
            }
        },
        "related_topics": ["security"],
        "difficulty": "intermediate",
        "last_updated": "2026-05-19"
    }
}

# Version-specific templates for identical files
templates = {
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
        "advanced": {
            "abstract": {
                "trigger_keywords": ["abstrait", "mixin", "template"],
                "snippet": "class CustomMixin(models.AbstractModel):",
                "warning": "Les modèles abstraits ne créent pas de table en base de données."
            }
        },
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
        "advanced": {
            "server_action": {
                "trigger_keywords": ["action serveur", "ir.actions.server", "python code action"],
                "snippet": "<record id=\"action_server\" model=\"ir.actions.server\">\n    <field name=\"model_id\" ref=\"model_custom_model\"/>\n    <field name=\"state\">code</field>\n    <field name=\"code\">action = records.my_method()</field>\n</record>",
                "warning": "Les actions serveur nécessitent la définition du champ model_id et state='code'."
            }
        },
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
        "advanced": {
            "batching": {
                "trigger_keywords": ["limit", "lot", "batch", "timeout", "grand volume"],
                "snippet": "records = self.search([('state', '=', 'draft')], limit=500)",
                "warning": "Assurez-vous de limiter la requête pour éviter les timeouts de cron et d'appeler env.cr.commit() si nécessaire."
            }
        },
        "related_topics": ["model"],
        "difficulty": "intermediate"
    }
}

# 1. Write v19 specific files
for topic, data in v19_files.items():
    file_path = os.path.join(base_path, "v19", f"{topic}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Updated {file_path}")

# 2. Write versioned templates for model, action_menu, cron
for v in ["17", "18", "19"]:
    for topic, template in templates.items():
        data = template.copy()
        data["version"] = v
        
        # Add version specific rules
        if topic == "model":
            if v == "17":
                data["rules"].append("Odoo 17: Support des types JSON pour les champs.")
            elif v == "18":
                data["rules"].append("Odoo 18: Optimisations de precompute pour les champs calculés du modèle.")
            elif v == "19":
                data["rules"].append("Odoo 19: Attention aux changements dans l'API des environnements pour les modèles isolés.")
        
        elif topic == "action_menu":
            if v == "17":
                data["rules"].append("Odoo 17: Menus supportent la définition de web_icon pour les applications racine.")
            elif v == "18":
                data["rules"].append("Odoo 18: Améliorations de la recherche dans ir.actions.act_window.")
            elif v == "19":
                data["rules"].append("Odoo 19: Nouveaux attributs possibles pour les actions de fenêtres modales.")
        
        elif topic == "cron":
            if v == "17":
                data["rules"].append("Odoo 17: Les crons en échec loguent plus de détails, gardez le code robuste.")
            elif v == "18":
                data["rules"].append("Odoo 18: Support avancé pour les triggers de cron conditionnels.")
            elif v == "19":
                data["rules"].append("Odoo 19: Les crons utilisent des timeouts plus stricts, favorisez le batching avec commit().")
        
        file_path = os.path.join(base_path, f"v{v}", f"{topic}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            print(f"Updated {file_path}")
