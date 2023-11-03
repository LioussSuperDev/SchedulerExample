import numpy as np
import os
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
    def __init__(self, batiment, etage, salle, type, dispo, effectifs=np.inf):
        self.batiment = batiment
        self.etage = etage
        self.salle = salle
        self.numero = -1
        self.effectifs = effectifs
        self.penalite_salle = 0
        self.type = type
        self.dispo = dispo

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
        self.tags = {}

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
        self.nb_heures_cours_mini_par_jour = 1

#Affichage simple après execution de la PLNE
def simple_print(demi_journees, profs, cours, salles, classes, afficher_profs, afficher_classes, afficher_salles, save_folder=None, scale=0.5):
    
    prof_folder = os.path.join(save_folder,"profs")
    classes_folder = os.path.join(save_folder,"classes")
    salles_folder = os.path.join(save_folder,"salles")
    if save_folder != None:
        os.makedirs(save_folder, exist_ok=True)
        os.makedirs(prof_folder, exist_ok=True)
        os.makedirs(classes_folder, exist_ok=True)
        os.makedirs(salles_folder, exist_ok=True)
    
    #Affichage par prof
    if afficher_profs:
        for prof in profs:

            #Write STDOUT
            if save_folder == None:
                print()
                print("==================================================")
                print()
                print("Emploi du temps de",prof.prenom,prof.nom)
                for dj_n,dj in enumerate(demi_journees):
                    print("demi-journée",dj_n+1,":::::::::::::::")
                    for cr_n,cr in enumerate(dj):
                        found = False
                        for co in cours:
                            if not co.prof is prof:
                                continue
                            if cr in co.organisation.creneaux:
                                found = True
                                if co.organisation.salle:
                                    num_salle = co.organisation.salle.batiment+str(co.organisation.salle.etage)+str(co.organisation.salle.salle)
                                else:
                                    num_salle = ""
                                if cr in prof.contraintes_pref_pas_cours:
                                    print(str((cr_n+1)*scale)+"h ["+str(prof.contraintes_pref_pas_cours[cr])+"] -",co.nom,"["+num_salle+"]","("+co.classe.niveau+" "+co.classe.spe+")")
                                else:
                                    print(str((cr_n+1)*scale)+"h -",co.nom,"["+num_salle+"] ("+co.classe.niveau+" "+co.classe.spe+")")
                        if cr in prof.contraintes_pas_cours:
                            print(str((cr_n+1)*scale)+"h [x] -")
                        elif cr in prof.contraintes_pref_pas_cours and not found:
                            print(str((cr_n+1)*scale)+"h ["+str(prof.contraintes_pref_pas_cours[cr])+"] -")
                        elif not found:
                            print(str((cr_n+1)*scale)+"h -")

            #Write file
            if save_folder != None:
                with open(os.path.join(prof_folder,prof.prenom+"-"+prof.nom+".txt"),"w+") as f:
                    for dj_n,dj in enumerate(demi_journees):
                        f.write("demi-journée "+str(dj_n+1)+" :::::::::::::::\n")
                        for cr_n,cr in enumerate(dj):
                            found = False
                            for co in cours:
                                if not co.prof is prof:
                                    continue
                                if cr in co.organisation.creneaux:
                                    found = True
                                    if co.organisation.salle:
                                        num_salle = co.organisation.salle.batiment+str(co.organisation.salle.etage)+str(co.organisation.salle.salle)
                                    else:
                                        num_salle = ""
                                    if cr in prof.contraintes_pref_pas_cours:
                                        f.write(str((cr_n+1)*scale)+"h ["+str(prof.contraintes_pref_pas_cours[cr])+"] - "+co.nom+" ["+num_salle+"] ("+co.classe.niveau+" "+co.classe.spe+")\n")
                                    else:
                                        f.write(str((cr_n+1)*scale)+"h - "+co.nom+" ["+num_salle+"] ("+co.classe.niveau+" "+co.classe.spe+")\n")
                            if cr in prof.contraintes_pas_cours:
                                f.write(str((cr_n+1)*scale)+"h [x] -\n")
                            elif cr in prof.contraintes_pref_pas_cours and not found:
                                f.write(str((cr_n+1)*scale)+"h ["+str(prof.contraintes_pref_pas_cours[cr])+"] -\n")
                            elif not found:
                                f.write(str((cr_n+1)*scale)+"h -\n")

    #Affichage par classe
    if afficher_classes:
        for cl in classes:

            #Write STDOUT
            if save_folder == None:
                print()
                print("==================================================")
                print()
                print("Emploi du temps de",cl.niveau,cl.spe)
                for dj_n,dj in enumerate(demi_journees):
                    print("demi-journée",dj_n+1,":::::::::::::::")
                    for cr_n,cr in enumerate(dj):
                        found = False
                        for co in cours:
                            if not co.classe is cl:
                                continue
                            if cr in co.organisation.creneaux:
                                found = True
                                if co.organisation.salle:
                                    num_salle = co.organisation.salle.batiment+str(co.organisation.salle.etage)+str(co.organisation.salle.salle)
                                else:
                                    num_salle = ""
                                if co.prof != None:
                                    print(str((cr_n+1)*scale)+"h -",co.nom,"["+num_salle+"] ("+co.prof.prenom,co.prof.nom+")")
                                else:
                                    print(str((cr_n+1)*scale)+"h -",co.nom,"["+num_salle+"]")
                        if not found:
                            print(str((cr_n+1)*scale)+"h -")

            #Write file
            if save_folder != None:
                with open(os.path.join(classes_folder,cl.niveau+"-"+cl.spe+".txt"),"w+") as f:
                    for dj_n,dj in enumerate(demi_journees):
                        f.write("demi-journée "+str(dj_n+1)+" :::::::::::::::\n")
                        for cr_n,cr in enumerate(dj):
                            found = False
                            for co in cours:
                                if not co.classe is cl:
                                    continue
                                if cr in co.organisation.creneaux:
                                    found = True
                                    if co.organisation.salle:
                                        num_salle = co.organisation.salle.batiment+str(co.organisation.salle.etage)+str(co.organisation.salle.salle)
                                    else:
                                        num_salle = ""
                                    if co.prof != None:
                                        f.write(str((cr_n+1)*scale)+"h - "+co.nom+" ["+num_salle+"] ("+co.prof.prenom+" "+co.prof.nom+")\n")
                                    else:
                                        f.write(str((cr_n+1)*scale)+"h - "+co.nom+" ["+num_salle+"]\n")
                            if not found:
                                f.write(str((cr_n+1)*scale)+"h -\n")


    #Affichage par salle
    if afficher_salles:
        for sl in salles:
            if save_folder == None:
                #Write STDOUT
                print()
                print("==================================================")
                print()
                print("Emploi du temps de",sl.batiment+str(sl.etage)+str(sl.salle))
                for dj_n,dj in enumerate(demi_journees):
                    print("demi-journée",dj_n+1," :::::::::::::::")
                    for cr_n,cr in enumerate(dj):
                        found = False
                        for co in cours:
                            if not co.organisation.salle is sl:
                                continue
                            if cr in co.organisation.creneaux:
                                found = True
                                if co.prof != None:
                                    print(str((cr_n+1)*scale)+"h -",co.nom,"["+co.prof.prenom,co.prof.nom+"]","("+co.classe.niveau+" "+co.classe.spe+")")
                                else:
                                    print(str((cr_n+1)*scale)+"h -",co.nom,"("+co.classe.niveau+" "+co.classe.spe+")")
                        if not found:
                            print(str((cr_n+1)*scale)+"h -")

            #Write file
            if save_folder != None:
                with open(os.path.join(salles_folder,sl.batiment+str(sl.etage)+str(sl.salle)+".txt"),"w+") as f:
                    for dj_n,dj in enumerate(demi_journees):
                        f.write("demi-journée "+str(dj_n+1)+" :::::::::::::::\n")
                        for cr_n,cr in enumerate(dj):
                            found = False
                            for co in cours:
                                if not co.organisation.salle is sl:
                                    continue
                                if cr in co.organisation.creneaux:
                                    found = True
                                    if co.prof != None:
                                        f.write(str((cr_n+1)*scale)+"h - "+co.nom+" ["+co.prof.prenom+" "+co.prof.nom+"] ("+co.classe.niveau+" "+co.classe.spe+")\n")
                                    else:
                                        f.write(str((cr_n+1)*scale)+"h - "+co.nom+" ("+co.classe.niveau+" "+co.classe.spe+")\n")
                            if not found:
                                f.write(str((cr_n+1)*scale)+"h -\n")