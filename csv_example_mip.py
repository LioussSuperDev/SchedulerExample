import csv
from toolbox import Professeur,Classe,Salle,Cours,Creneau,simple_print
from core_mip import build_compute_plne
import math
from datetime import date as dt
from datetime import datetime as dtt

######################################################
######################################################
########### PARAMETRES ###############################
######################################################
######################################################

duree_demi_journee = 4
nombre_demi_journees = 10

penalite_prof_1 = 100000
penalite_prof_2 = 10000

penalite_salle_partagee = 1
penalite_salle_eval = 100
bonus_prof_salle = 1

penalite_cours_creneau_seul = 1
penalite_journee_travaillee = 100

week_number = 1

fichier_contraintes = "./exemples/week"+str(week_number)+"/contraintes.csv"
fichier_cours = "./exemples/week"+str(week_number)+"/cours.csv"
fichier_salles = "./exemples/week"+str(week_number)+"/salles.csv"
fichier_effectifs = "./exemples/week"+str(week_number)+"/effectifs.csv"

######################################################
######################################################
######################################################
################# FONCTIONS DATES ####################

def date_to_creneaux(date, creneau, demi_journees, duree):
    creneaux = []
    is_afternoon = "PM" in creneau
    demi_journee = dtt.strptime(date, "%d/%m/%Y").weekday()*2 + int(is_afternoon)

    creneau_debut = int(creneau[:4].split("-")[1]) - 1

    if creneau[4:] == "b" or int(duree) != duree:
        creneau_fin = creneau_debut + int(duree)
    else:
        creneau_fin = creneau_debut + int(duree) - 1

    for creneau_idx in range(creneau_debut,creneau_fin+1):
        if creneau_idx < len(demi_journees[demi_journee]):
            creneaux.append(demi_journees[demi_journee][creneau_idx])
    return creneaux

######################################################
######################################################
######################################################
######################################################

##############################################################
# REMPLISSAGE DES CRENEAUX ###################################
##############################################################

demi_journees = []


for dj in range(nombre_demi_journees):
    demi_journee = [Creneau(None)]
    for i in range(duree_demi_journee-1):
        demi_journee.append(Creneau(demi_journee[i]))
        demi_journee[i].set_suivant(demi_journee[i+1])
    demi_journees.append(demi_journee)
        
creneaux = []
i = 0
for dj in demi_journees:
    for cr in dj:
        creneaux.append(cr)
        cr.numero = i
        i += 1

##############################################################
# REMPLISSAGE DES PROFS ######################################
##############################################################

profs = {}

with open(fichier_contraintes) as csvfile:
    spamreader = csv.reader(csvfile,delimiter=";")
    for row_n,row in enumerate(spamreader):
        if row_n == 0 or row[0] == "":
            continue

        prof = Professeur(row[0],"")
        for i in range(1,len(row)-1):
            # creneau_index = int(((i-1)*2)%8)
            # dj_index = ((i-1)*2)//8
            creneau_index = int((i-1)%4)
            dj_index = (i-1)//4
            if row[i] == "0":
                prof.contraintes_pas_cours.append(demi_journees[dj_index][creneau_index])
                # prof.contraintes_pas_cours.append(demi_journees[dj_index][creneau_index+1])
            elif row[i] == "1":
                prof.contraintes_pref_pas_cours[demi_journees[dj_index][creneau_index]] = penalite_prof_1
                # prof.contraintes_pref_pas_cours[demi_journees[dj_index][creneau_index+1]] = penalite_prof_1
            elif row[i] == "2":
                prof.contraintes_pref_pas_cours[demi_journees[dj_index][creneau_index]] = penalite_prof_2
                # prof.contraintes_pref_pas_cours[demi_journees[dj_index][creneau_index+1]] = penalite_prof_2
        profs[prof.nom] = prof



################################################################
# REMPLISSAGE DES GROUPES ######################################
################################################################

groupes = {}

with open(fichier_effectifs) as csvfile:
    spamreader = csv.reader(csvfile,delimiter=";")
    for row_n,row in enumerate(spamreader):
        if row_n == 0:
            continue
        annee = row[0]
        groupe = row[1]
        effectifs = int(row[2])
        if groupe != "":
            groupe_id = annee + "." + groupe
        else:
            groupe_id = annee

        if not groupe_id in groupes:
            groupes[groupe_id] = Classe(annee,groupe,effectifs)

#on met les relations classe entière-demi groupe
for groupe in groupes:
    if groupes[groupe].spe == "":
        for groupe2 in groupes:
            if groupes[groupe2].niveau == groupes[groupe].niveau and groupes[groupe2].spe != "":
                groupes[groupe].mutex.append(groupes[groupe2])

################################################################
# REMPLISSAGE DES COURS ########################################
################################################################

cours = []

with open(fichier_cours) as csvfile:
    spamreader = csv.reader(csvfile,delimiter=";")
    for row_n,row in enumerate(spamreader):
        if row_n == 0 or row[0] == "FIN" or row[0] == "":
            continue
        annee = row[0]
        groupe = row[1]
        type_m = row[2]
        # duree = int(row[3])*2
        duree = int(math.ceil(float(row[3])))
        matiere = row[4].strip()
        contenu = row[5]
        _id = row[14]

        date = row[11]
        creneau = row[12]

        prof = row[6]
        if groupe != "":
            groupe_id = annee + "." + groupe
        else:
            groupe_id = annee

        groupe = groupes[groupe_id]
        if prof == "admin" or type_m == "auto":
            real_prof = None
        else:
            real_prof = profs[prof]
        
        c = Cours(type_m+" - "+matiere,real_prof,groupes[groupe_id],duree)

        if date != "" and creneau != "":
            c.contrainte_dans_creneaux += date_to_creneaux(date, creneau, demi_journees, float(row[3]))

        if row[8] == "Vrai":
            c.tags["info"] = True
        c.tags["matiere"] = matiere
        c.tags["_id"] = _id
        cours.append(c)

################################################################
# REMPLISSAGE DES SALLES #######################################
################################################################

salles = []

with open(fichier_salles) as csvfile:
    spamreader = csv.reader(csvfile,delimiter=";")
    for row_n,row in enumerate(spamreader):
        if row_n == 0 or row[0] == "":
            continue
        nom = row[1]
        effectifs = int(row[3])
        type_salle = row[4]
        is_info = (row[2] == "info")

        salle = Salle("","",nom,effectifs)

        #Contraintes salles info
        for c in cours:
            if "info" in c.tags:
                c.contraintes_salle.append(salle)

        #Contraintes salles lointaines
        if "Odeum" in nom:
            salle.penalite_salle += penalite_salle_eval
        elif type_salle != "pleine":
            salle.penalite_salle += penalite_salle_partagee
        
        #Préférences des profs
        if row[5] != "":
            prof_pref_salle = row[5].split(",")
            for prof in prof_pref_salle:
                profs[prof].bonus_salle[salle] = bonus_prof_salle
        
        #Nécessité matière
        if row[6] != "":
            matiere_imposee_salle = row[6].split(",")
            for matiere in matiere_imposee_salle:
                m_name = matiere.split("=")[0]
                for c in cours:
                    if c.tags["matiere"] == m_name:
                        c.contraintes_salle.append(salle)

        salles.append(salle)

################################################################
# STANDARDISATION ##############################################
################################################################

classes = list(groupes.values())
for i,groupe in enumerate(classes):
    groupe.numero = i
profs = list(profs.values())
for i,prof in enumerate(profs):
    prof.numero = i
for i,cour in enumerate(cours):
    cour.numero = i
for i,salle in enumerate(salles):
    salle.numero = i

#Génération des matrices pour la PLNE à partir de la modélisation
################################## CONVERSION EN MATRICES / EXECUTION DE LA PLNE / ON ACTUALISE NOS OBJETS AVEC LE RESULTAT ####################################################################
print("taille groupes :",len(classes))
print("taille profs :",len(profs))
print("taille cours :",len(cours))
print("taille salles :",len(salles))
print("taille creneaux :",len(creneaux))
res = build_compute_plne(cours, creneaux, salles, classes, profs, demi_journees=demi_journees, penalite_cours_creneau_seul=penalite_cours_creneau_seul, penalite_journee_travaillee=penalite_journee_travaillee, verbose=True, max_time=7200)

################################# AFFICHAGE ####################################################################################################################################################

afficher_profs = True
afficher_classes = True
afficher_salles = True

#simple_print(demi_journees,profs,cours,salles,classes,afficher_profs,afficher_classes,afficher_salles,save_folder="./results/csv_example/week"+str(week_number),scale=1)