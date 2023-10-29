import numpy as np

#classe de chaîne créneau
class Creneau:
    def __init__(self, precedent):
        self.precedent = precedent
        self.suivant = None
        self.numero = -1
    
    def set_suivant(self, suivant):
        self.suivant = suivant

    def get_suivants(self):
        suivants = [self]
        suivant = self.suivant
        while suivant != None:
            suivants.append(suivant)
            suivant = suivant.suivant
        return suivants

#définition des classes
class Classe:
    def __init__(self, niveau, spe, effectifs=0):
        self.niveau = niveau
        self.spe = spe
        self.mutex = []
        self.effectifs = effectifs
        self.numero = -1

#définition des salles
class Salle:
    def __init__(self, batiment, etage, salle, effectifs=np.inf):
        self.batiment = batiment
        self.etage = etage
        self.salle = salle
        self.numero = -1
        self.effectifs = effectifs
        self.penalite_salle = 0

#définition des cours
class Cours:

    class Organisation:
        def __init__(self, creneaux, salle):
            self.creneaux = creneaux
            self.salle = salle

    def __init__(self, nom, prof, classe, duree):
        self.nom = nom #Cours de Mathématiques
        self.prof = prof #Objet qui représente M. DI SCALA
        self.classe = classe #Object qui représente la classe L1 Info
        self.duree = duree #Longueur en créneaux 
        self.contraintes_salle = [] #Contraintes des salles dans lesquelles ce cours doit avoir lieu
        self.numero = -1
        self.organisation = None
        self.contrainte_dans_creneaux = [] #Si vide aucune contrainte, si contient des créneaux => ce cours ne peut être que durant ces créneaux
        self.tags = []

    def set_organisation(self, creneaux, salle):
        self.organisation = self.Organisation(creneaux, salle)

#définition des professeurs
class Professeur:
    def __init__(self, nom, prenom):
        self.nom = nom
        self.prenom = prenom
        self.contraintes_pas_cours = [] #Contraintes des créneaux durant lesquelles ce prof ne peut pas venir
        self.contraintes_pref_pas_cours = {} #Dictionnaire (Contraintes des créneaux durant lesquelles ce prof ne veut pas venir => pénalité)
        self.bonus_salle = {} #Dictionnaire (Salle dans lequel le prof a cours => bonus)