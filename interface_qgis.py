from qgis.core import QgsProject, QgsVectorLayer, QgsSimpleLineSymbolLayer, QgsRuleBasedRenderer, QgsSymbol
import os
from qgis.PyQt.QtWidgets import QWidget, QPushButton, QVBoxLayout, QAction
from qgis.PyQt.QtCore import Qt
from qgis.utils import iface
from PyQt5.QtGui import QColor


# Créer une fenêtre principale avec 6 boutons
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Initialisation')
        self.setGeometry(100, 100, 300, 200)

        # Disposition verticale pour les boutons
        layout = QVBoxLayout()

        nom_bouton = ["ville avant la tempete", "ville apres la tempete", "batiments prioritaires", "infrastructures prioritaires"]

        # Création des 6 boutons
        for i in range(4):
            button = QPushButton(f'{nom_bouton[i]}', self)
            button.clicked.connect(lambda checked, num=nom_bouton[i]: self.run_script(num))
            layout.addWidget(button)

        self.setLayout(layout)

    # Fonction pour exécuter le script correspondant à chaque bouton
    def run_script(self, button_num):
        if button_num == "ville avant la tempete":
            # Initialiser le projet actuel de QGIS
            project = QgsProject.instance()

            # Ajouter OpenStreetMap comme une couche XYZ
            osm_layer = QgsRasterLayer("type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png", "OpenStreetMap", "wms")
            if not osm_layer.isValid():
                print("La couche OpenStreetMap n'a pas pu être chargée.")
            else:
                project.addMapLayer(osm_layer)

            # Chemin vers le dossier contenant les fichiers
            folder_path = "C:/Users/mathi/Downloads/Doc"  # Remplace par le chemin vers ton dossier

            # Importer la couche "batiments.dbf"
            batiments_layer = QgsVectorLayer(os.path.join(folder_path, "batiments.dbf"), "Bâtiments", "ogr")
            if not batiments_layer.isValid():
                print("La couche Bâtiments n'a pas pu être chargée.")
            else:
                symbol = batiments_layer.renderer().symbol()
                symbol.setColor(Qt.green)
                project.addMapLayer(batiments_layer)
                project.addMapLayer(batiments_layer)

            # Importer la couche "infrastructures.dbf"
            infrastructures_layer = QgsVectorLayer(os.path.join(folder_path, "infrastructures.dbf"), "Infrastructures", "ogr")
            if not infrastructures_layer.isValid():
                print("La couche Infrastructures n'a pas pu être chargée.")
            else:
                # Appliquer le style vert avec épaisseur 0,6
                symbol = infrastructures_layer.renderer().symbol()
                symbol.setColor(Qt.green)
                
                # Modifier l'épaisseur du trait
                if isinstance(symbol.symbolLayer(0), QgsSimpleLineSymbolLayer):
                    symbol.symbolLayer(0).setWidth(0.6)
                
                project.addMapLayer(infrastructures_layer)
                print("Couche Infrastructures ajoutée avec style vert.")

            print("Les couches ont été importées avec succès.")
        elif button_num == "ville apres la tempete":
            # Obtenir la couche "Infrastructures" existante dans le projet
            infra_layers = QgsProject.instance().mapLayersByName("Infrastructures")
            if not infra_layers:
                print("La couche Infrastructures n'est pas présente dans le projet.")
            else:
                infra_layer = infra_layers[0]
                print("Couche Infrastructures trouvée avec succès.")

                # Chemin vers le fichier CSV
                folder_path = "C:/Users/mathi/Downloads/electric_network_planning_project"
                infra_state_path = os.path.join(folder_path, "infra_state.csv")
                infra_state_layer = QgsVectorLayer(infra_state_path, "infra_state", "ogr")
                
                if not infra_state_layer.isValid():
                    print("La table infra_state n'a pas pu être chargée.")
                else:
                    QgsProject.instance().addMapLayer(infra_state_layer)
                    print("Table Infra_state ajoutée avec succès.")

                    # Début de l'édition de la couche Infrastructures
                    infra_layer.startEditing()
                    
                    # Ajouter les champs de la couche infra_state dans la couche Infrastructures
                    infra_state_fields = [field for field in infra_state_layer.fields() if field.name() != 'infra_id']
                    for field in infra_state_fields:
                        infra_layer.addAttribute(QgsField(field.name(), field.type()))
                    
                    infra_layer.updateFields()
                    
                    # Créer un dictionnaire pour correspondre infra_id avec les autres valeurs dans infra_state
                    infra_state_data = {}
                    for feature in infra_state_layer.getFeatures():
                        infra_state_data[feature['infra_id']] = feature
                        
                    # Remplir les attributs de la couche Infrastructures avec les valeurs jointes
                    for feature in infra_layer.getFeatures():
                        infra_id = feature['infra_id']
                        if infra_id in infra_state_data:
                            # Mettre à jour les valeurs de chaque champ ajouté
                            for field in infra_state_fields:
                                infra_layer.changeAttributeValue(feature.id(), infra_layer.fields().indexOf(field.name()), infra_state_data[infra_id][field.name()])

                    # Fin de l'édition
                    infra_layer.commitChanges()
                    print("Les données de jointure ont été intégrées directement dans la couche Infrastructures.")

                    line_width = 0.8

                    # Appliquer la symbologie basée sur des règles
                    symbol = QgsSymbol.defaultSymbol(infra_layer.geometryType())
                    root_rule = QgsRuleBasedRenderer.Rule(symbol)

                    # Règle pour les infrastructures "intacte" (par exemple, en vert)
                    rule_intacte = root_rule.clone()
                    rule_intacte.setFilterExpression('"infra_type" = \'infra_intacte\'')
                    rule_intacte.symbol().setColor(QColor("green"))
                    rule_intacte.symbol().setWidth(line_width)
                    rule_intacte.setLabel("Intacte")

                    # Règle pour les infrastructures "à réparer" (par exemple, en rouge)
                    rule_a_reparer = root_rule.clone()
                    rule_a_reparer.setFilterExpression('"infra_type" = \'a_remplacer\'')
                    rule_a_reparer.symbol().setColor(QColor("red"))
                    rule_a_reparer.symbol().setWidth(line_width)
                    rule_a_reparer.setLabel("À remplacer")

                    # Ajouter les règles à la symbologie
                    root_rule.appendChild(rule_intacte)
                    root_rule.appendChild(rule_a_reparer)

                    # Appliquer la symbologie basée sur des règles à la couche
                    renderer = QgsRuleBasedRenderer(root_rule)
                    infra_layer.setRenderer(renderer)
                    infra_layer.triggerRepaint()

                    print("Symbologie basée sur les règles appliquée avec succès à la couche Infrastructures.")
            # Obtenir la couche "Bâtiments" existante dans le projet
            batiments_layers = QgsProject.instance().mapLayersByName("Bâtiments")
            if not batiments_layers:
                print("La couche Bâtiments n'est pas présente dans le projet.")
            else:
                batiments_layer = batiments_layers[0]
                print("Couche Infrastructures trouvée avec succès.")

                # Chemin vers le fichier CSV
                folder_path = "C:/Users/mathi/Downloads/electric_network_planning_project"
                batiments_sans_electricite_path = os.path.join(folder_path, "batiments_sans_electricite.csv")
                batiments_sans_electricite_layer = QgsVectorLayer(batiments_sans_electricite_path, "batiments_sans_electricite", "ogr")
                
                if not batiments_sans_electricite_layer.isValid():
                    print("La table batiments_sans_electricite n'a pas pu être chargée.")
                else:
                    QgsProject.instance().addMapLayer(batiments_sans_electricite_layer)
                    print("Table batiments_sans_electricite ajoutée avec succès.")

                    # Début de l'édition de la couche Infrastructures
                    batiments_layer.startEditing()
                    
                    # Ajouter les champs de la couche infra_state dans la couche Infrastructures
                    batiments_sans_electricite_fields = [field for field in batiments_sans_electricite_layer.fields() if field.name() != 'id_bat']
                    for field in batiments_sans_electricite_fields:
                        batiments_layer.addAttribute(QgsField(field.name(), field.type()))
                    
                    batiments_layer.updateFields()
                    
                    # Créer un dictionnaire pour correspondre id_bat avec les autres valeurs dans infra_state
                    batiments_sans_electricite_data = {}
                    for feature in batiments_sans_electricite_layer.getFeatures():
                        batiments_sans_electricite_data[feature['id_bat']] = feature
                        
                    # Remplir les attributs de la couche Infrastructures avec les valeurs jointes
                    for feature in batiments_layer.getFeatures():
                        id_bat = feature['id_bat']
                        if id_bat in batiments_sans_electricite_data:
                            # Mettre à jour les valeurs de chaque champ ajouté
                            for field in batiments_sans_electricite_fields:
                                batiments_layer.changeAttributeValue(feature.id(), batiments_layer.fields().indexOf(field.name()), batiments_sans_electricite_data[id_bat][field.name()])

                    # Fin de l'édition
                    batiments_layer.commitChanges()
                    print("Les données de jointure ont été intégrées directement dans la couche Batiments.")


                # Créer une symbologie basée sur des règles
                symbol = QgsSymbol.defaultSymbol(batiments_layer.geometryType())

                # Définir les règles
                root_rule = QgsRuleBasedRenderer.Rule(symbol)

                # Règle pour les entités avec state non nulle (par exemple, en vert)
                rule_non_null = root_rule.clone()
                rule_non_null.setFilterExpression('"state" IS NOT NULL')
                rule_non_null.symbol().setColor(QColor("red"))
                rule_non_null.setLabel("a réparer")

                # Règle pour les entités avec state nulle (par exemple, en rouge)
                rule_null = root_rule.clone()
                rule_null.setFilterExpression('"state" IS NULL')
                rule_null.symbol().setColor(QColor("green"))
                rule_null.setLabel("intacte")

                # Ajouter les règles à la symbologie
                root_rule.appendChild(rule_non_null)
                root_rule.appendChild(rule_null)

                # Appliquer la symbologie basée sur des règles à la couche
                renderer = QgsRuleBasedRenderer(root_rule)
                batiments_layer.setRenderer(renderer)
                batiments_layer.triggerRepaint()

                print("Symbologie basée sur les règles appliquée avec succès à la couche Bâtiments.")


        elif button_num == "batiments prioritaires":
            # Obtenir la couche "Bâtiments" existante dans le projet
            batiments_layers = QgsProject.instance().mapLayersByName("Bâtiments")
            if not batiments_layers:
                print("La couche Bâtiments n'est pas présente dans le projet.")
            else:
                batiments_layer = batiments_layers[0]
                print("Couche Bâtiments trouvée avec succès.")

                # Définir la couleur de départ (vert clair) et la couleur de fin (rouge vif)
                color_start = QColor(144, 238, 144)  # Vert clair
                color_end = QColor(255, 69, 0)       # Rouge flashy

                # Plage de priorité
                min_priority = 1
                max_priority = 85
                step = 15

                # Créer le renderer basé sur des règles
                symbol = QgsSymbol.defaultSymbol(batiments_layer.geometryType())
                rule_based_renderer = QgsRuleBasedRenderer(symbol)
                root_rule = rule_based_renderer.rootRule()

                # Créer des règles pour chaque intervalle de priorité
                for i in range(min_priority, max_priority, step):
                    # Calculer la couleur de l'intervalle
                    color = QColor(
                        int(color_start.red() + (color_end.red() - color_start.red()) * (i / max_priority)),
                        int(color_start.green() + (color_end.green() - color_start.green()) * (i / max_priority)),
                        int(color_start.blue() + (color_end.blue() - color_start.blue()) * (i / max_priority))
                    )

                    # Créer un symbole avec la couleur calculée
                    interval_symbol = QgsSymbol.defaultSymbol(batiments_layer.geometryType())
                    interval_symbol.setColor(color)
                    if interval_symbol.type() == QgsSymbol.Marker:
                        interval_symbol.setSize(3.0)
                    elif interval_symbol.type() == QgsSymbol.Line:
                        interval_symbol.setWidth(0.8)

                    # Définir la règle pour cet intervalle
                    label = f"{i} - {i + step - 1}"
                    expression = f'"priority" >= {i} AND "priority" < {i + step}'
                    
                    range_rule = QgsRuleBasedRenderer.Rule(interval_symbol)
                    range_rule.setFilterExpression(expression)
                    range_rule.setLabel(label)

                    # Ajouter la règle à la racine
                    root_rule.appendChild(range_rule)

                # Ajouter une règle d'exclusion pour toute valeur de priorité en dehors de la plage définie
                exclude_symbol = QgsSymbol.defaultSymbol(batiments_layer.geometryType())
                exclude_symbol.setColor(QColor(255, 255, 255, 0))  # Couleur transparente
                exclude_rule = QgsRuleBasedRenderer.Rule(exclude_symbol)
                exclude_rule.setFilterExpression(f'"priority" < {min_priority} OR "priority" >= {max_priority}')
                exclude_rule.setLabel("Exclu")
                root_rule.appendChild(exclude_rule)

                # Appliquer le renderer basé sur des règles à la couche
                batiments_layer.setRenderer(rule_based_renderer)
                batiments_layer.triggerRepaint()

                print("Symbologie par intervalle appliquée avec succès à la couche Bâtiments.")

        elif button_num == "infrastructures prioritaires":
            # Obtenir la couche "Infrastructures" existante dans le projet
            infra_layers = QgsProject.instance().mapLayersByName("Infrastructures")
            if not infra_layers:
                print("La couche Infrastructures n'est pas présente dans le projet.")
            else:
                infra_layer = infra_layers[0]
                print("Couche Infrastructures trouvée avec succès.")

                # Chemin vers le fichier CSV
                folder_path = "C:/Users/mathi/Downloads/electric_network_planning_project"
                infra_state_path = os.path.join(folder_path, "infra_priority.csv")
                infra_state_layer = QgsVectorLayer(infra_state_path, "infra_priority", "ogr")
                
                if not infra_state_layer.isValid():
                    print("La table infra_state n'a pas pu être chargée.")
                else:
                    QgsProject.instance().addMapLayer(infra_state_layer)
                    print("Table Infra_state ajoutée avec succès.")

                    # Début de l'édition de la couche Infrastructures
                    infra_layer.startEditing()
                    
                    # Ajouter les champs de la couche infra_state dans la couche Infrastructures
                    infra_state_fields = [field for field in infra_state_layer.fields() if field.name() != 'infra_id']
                    for field in infra_state_fields:
                        infra_layer.addAttribute(QgsField(field.name(), field.type()))
                    
                    infra_layer.updateFields()
                    
                    # Créer un dictionnaire pour correspondre infra_id avec les autres valeurs dans infra_state
                    infra_state_data = {}
                    for feature in infra_state_layer.getFeatures():
                        infra_state_data[feature['infra_id']] = feature
                        
                    # Remplir les attributs de la couche Infrastructures avec les valeurs jointes
                    for feature in infra_layer.getFeatures():
                        infra_id = feature['infra_id']
                        if infra_id in infra_state_data:
                            # Mettre à jour les valeurs de chaque champ ajouté
                            for field in infra_state_fields:
                                infra_layer.changeAttributeValue(feature.id(), infra_layer.fields().indexOf(field.name()), infra_state_data[infra_id][field.name()])

                    # Fin de l'édition
                    infra_layer.commitChanges()
                    print("Les données de jointure ont été intégrées directement dans la couche Infrastructures.")


            # Obtenir la couche "Bâtiments" existante dans le projet
            batiments_layers = QgsProject.instance().mapLayersByName("Infrastructures")
            if not batiments_layers:
                print("La couche BâtimeInts n'est pas présente dans le projet.")
            else:
                batiments_layer = batiments_layers[0]
                print("Couche Bâtiments trouvée avec succès.")

                # Définir la couleur de départ (vert clair) et la couleur de fin (rouge vif)
                color_start = QColor(144, 238, 144)  # Vert clair
                color_end = QColor(255, 69, 0)       # Rouge flashy

                # Plage de priorité
                min_priority = 1
                max_priority = 197
                step = 34

                # Créer le renderer basé sur des règles
                symbol = QgsSymbol.defaultSymbol(batiments_layer.geometryType())
                rule_based_renderer = QgsRuleBasedRenderer(symbol)
                root_rule = rule_based_renderer.rootRule()

                # Créer des règles pour chaque intervalle de priorité
                for i in range(min_priority, max_priority, step):
                    # Calculer la couleur de l'intervalle
                    color = QColor(
                        int(color_start.red() + (color_end.red() - color_start.red()) * (i / max_priority)),
                        int(color_start.green() + (color_end.green() - color_start.green()) * (i / max_priority)),
                        int(color_start.blue() + (color_end.blue() - color_start.blue()) * (i / max_priority))
                    )

                    # Créer un symbole avec la couleur calculée
                    interval_symbol = QgsSymbol.defaultSymbol(batiments_layer.geometryType())
                    interval_symbol.setColor(color)
                    if interval_symbol.type() == QgsSymbol.Marker:
                        interval_symbol.setSize(2.0)
                    elif interval_symbol.type() == QgsSymbol.Line:
                        interval_symbol.setWidth(1.1)

                    # Définir la règle pour cet intervalle
                    label = f"{i} - {i + step - 1}"
                    expression = f'"priority" >= {i} AND "priority" < {i + step}'
                    
                    range_rule = QgsRuleBasedRenderer.Rule(interval_symbol)
                    range_rule.setFilterExpression(expression)
                    range_rule.setLabel(label)

                    # Ajouter la règle à la racine
                    root_rule.appendChild(range_rule)

                # Ajouter une règle d'exclusion pour toute valeur de priorité en dehors de la plage définie
                exclude_symbol = QgsSymbol.defaultSymbol(batiments_layer.geometryType())
                exclude_symbol.setColor(QColor(255, 255, 255, 0))  # Couleur transparente
                exclude_rule = QgsRuleBasedRenderer.Rule(exclude_symbol)
                exclude_rule.setFilterExpression(f'"priority" < {min_priority} OR "priority" >= {max_priority}')
                exclude_rule.setLabel("Exclu")
                root_rule.appendChild(exclude_rule)

                # Appliquer le renderer basé sur des règles à la couche
                batiments_layer.setRenderer(rule_based_renderer)
                batiments_layer.triggerRepaint()

                print("Symbologie par intervalle appliquée avec succès à la couche Bâtiments.")


# Fonction pour créer le bouton principal dans QGIS
def create_main_action():
    # Créer une action pour la barre d'outils
    main_action = QAction("Ouvrir Interface 6 Boutons", iface.mainWindow())
    
    # Connecter le clic de l'action à l'ouverture de la fenêtre MainWindow
    main_action.triggered.connect(open_main_window)
    
    # Ajouter l'action à la barre d'outils de QGIS
    iface.addToolBarIcon(main_action)
    print("Bouton principal ajouté à l'interface QGIS")

# Fonction pour ouvrir la fenêtre avec les 6 boutons
def open_main_window():
    window = MainWindow()
    window.show()

# Démarrer l'action principale
create_main_action()
