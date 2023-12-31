import csv
from toolbox import Professeur,Classe,Salle,Cours,Creneau,simple_print
from core_mip import build_compute_plne
import math
from datetime import datetime as dtt,timedelta
import numpy as np

######################################################
######################################################
########### PARAMETRES ###############################
######################################################
######################################################

contraintes_salles = False #Assigne des salles (augmente de beaucoup le temps de calcul)
mip_preprocess = True #Active le preprocessing du solver mip; peut accélérer (ou parfois ralentir) le calcul

duree_demi_journee = 4
nombre_demi_journees = 10

penalite_prof_1 = 1000000
penalite_prof_2 = 100000000

penalite_salle_partagee = 1
penalite_salle_eval = 100
bonus_prof_salle = 1

penalite_cours_creneau_seul = 1
penalite_journee_travaillee = 20

week_number = 1
date_lundi = "22/01/2024"

fichier_contraintes = "./exemples/week"+str(week_number)+"/contraintes.csv"
fichier_cours = "./exemples/week"+str(week_number)+"/cours.csv"
fichier_salles = "./exemples/week"+str(week_number)+"/salles.csv"
fichier_effectifs = "./exemples/week"+str(week_number)+"/effectifs.csv"

max_time = 3600 #Temps à attendre avant de couper le solver après avoir trouvé une première solution

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

def creneau_to_date(monday_date_string, creneau):
    day = (dtt.strptime(monday_date_string, "%d/%m/%Y") + timedelta(days=creneau.numero//8)).strftime("%d/%m/%Y")
    cr = "PM-" if creneau.numero%8 >= 4 else "AM-"
    cr += str((creneau.numero%8)+1)+"a"
    return day,cr


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
print(creneau_to_date(date_lundi,creneaux[10]))

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

        prof.nb_heures_cours_mini_par_jour = int(row[1])
        for i in range(2,len(row)-1):
            creneau_index = int((i-2)%4)
            dj_index = (i-2)//4
            if row[i] == "0":
                prof.contraintes_pas_cours.append(demi_journees[dj_index][creneau_index])
            elif row[i] == "1":
                prof.contraintes_pref_pas_cours[demi_journees[dj_index][creneau_index]] = penalite_prof_1
            elif row[i] == "2":
                prof.contraintes_pref_pas_cours[demi_journees[dj_index][creneau_index]] = penalite_prof_2
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
if contraintes_salles:
    with open(fichier_salles) as csvfile:
        spamreader = csv.reader(csvfile,delimiter=";")
        for row_n,row in enumerate(spamreader):
            if row_n == 0 or row[0] == "":
                continue
            nom = row[1]
            effectifs = row[4]
            type_salle = int(row[3])
            is_info = (row[2] == "info")

            salle = Salle("","",nom,effectifs,row[2],type_salle)

            #Contraintes salles info
            for c in cours:
                if "info" in c.tags == is_info:
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
if contraintes_salles:
    for i,salle in enumerate(salles):
        salle.numero = i

#Génération des matrices pour la PLNE à partir de la modélisation
################################## CONVERSION EN MATRICES / EXECUTION DE LA PLNE / ON ACTUALISE NOS OBJETS AVEC LE RESULTAT ####################################################################
print("taille groupes :",len(classes))
print("taille profs :",len(profs))
print("taille cours :",len(cours))
if contraintes_salles:
    print("taille salles :",len(salles))
print("taille creneaux :",len(creneaux))
res = build_compute_plne(cours, creneaux, salles, classes, profs, demi_journees=demi_journees, penalite_cours_creneau_seul=penalite_cours_creneau_seul, penalite_journee_travaillee=penalite_journee_travaillee, verbose=True, max_time=max_time, contraintes_salles=contraintes_salles, mip_preprocess=mip_preprocess)

################################# AFFICHAGE ####################################################################################################################################################

afficher_profs = True
afficher_classes = True
afficher_salles = True

simple_print(demi_journees,profs,cours,salles,classes,afficher_profs,afficher_classes,afficher_salles,save_folder="./results/csv_example/week"+str(week_number),scale=1)

#Création format standardisé
with open(fichier_cours) as csvfileread:
    spamreader = csv.reader(csvfileread, delimiter=";")
    with open("./results/csv_example/week"+str(week_number)+"/cours.csv", "w+", newline='') as csvfilewrite:
        writer = csv.writer(csvfilewrite, delimiter=';')
        rows = []
        for i,row in enumerate(spamreader):
            if i != 0:
                for cour in cours:
                    if cour.tags["_id"] == row[-1]:
                        creneau = None
                        for cr in cour.organisation.creneaux:
                            if creneau == None or cr.numero < creneau.numero:
                                creneau = cr
                        sl = cour.organisation.salle
                        if sl != None and contraintes_salles:
                            if sl.dispo!="pleine":
                                comment="{!}"
                            else:
                                comment=""
                            if row[-2] == "":
                                row[-2] = str(sl.salle)+" ("+str(sl.type)+":"+str(sl.effectifs)+") "+comment
                        date,creneau = creneau_to_date(date_lundi, creneau)
                        if row[-3] == "":
                            row[-3] = creneau
                        if row[-4] == "":
                            row[-4] = date

            writer.writerow(row)