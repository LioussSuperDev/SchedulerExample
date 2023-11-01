from toolbox import Professeur,Classe,Salle,Cours,Creneau,simple_print
from core_mip import build_compute_plne

#8 créneaux par demi-journée
duree_demi_journee = 8
nombre_demi_journees = 3

#définition de 3 demi-journées et remplissage des créneaux
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


#Creation des profs
discala = Professeur("DI SCALA", "Pascal")
for i in range(8):
    discala.contraintes_pas_cours.append(demi_journees[0][i]) #pas cours la première demi-journée
for i in range(4):
    discala.contraintes_pas_cours.append(demi_journees[1][4+i]) #pas cours les 2 dernières heures de la 2ème mi-journée
for i in range(8):
    discala.contraintes_pref_pas_cours[demi_journees[1][i]] = 2 #pas cours la deuxième mi-journée (contrainte de pénalité de 2 pts)
dupont = Professeur("DUPONT", "Martin")

smith = Professeur("SMITH", "Will")
for i in range(4):
    smith.contraintes_pas_cours.append(demi_journees[1][2+i]) #pas cours au milieu de la deuxième mi-journée
for i in range(8):
    smith.contraintes_pref_pas_cours[demi_journees[1][i]] = 4 #pas cours la deuxième mi-journée (contrainte de pénalité de 4 pts)
benoit16 = Professeur("16", "Benoit")

christ = Professeur("CHRIST", "Jésus")

sinatra = Professeur("SINATRA", "Frank")
for i in range(8):
    sinatra.contraintes_pas_cours.append(demi_journees[1][i]) #pas cours la deuxième demi-journée

profs = [discala, dupont, smith, benoit16, christ, sinatra]
for i,prof in enumerate(profs):
    prof.numero = i

#Creation des salles
I415 = Salle("I", 4, 15)
I416 = Salle("I", 4, 16) #Salle pour la musique
I417 = Salle("I", 4, 17) #Salle pour la cuisine

salles = [I415, I416, I417]
for i,sl in enumerate(salles):
    sl.numero = i

#définition des classes
L1info = Classe("L1","info")
L1maths = Classe("L1","maths")
BTSinfo = Classe("BTS","info")
BacProCuisine = Classe("Bac Pro","cuisine")
BTSinfo.mutex.append(BacProCuisine)
classes = [L1info, L1maths, BTSinfo, BacProCuisine]

#définition des cours
c1 = Cours("Cours de Python", discala, L1info, 4)
c2 = Cours("Cours de Stats", dupont, L1maths, 4)
c3 = Cours("Cours d'Algèbre", dupont, L1maths, 6)
c4 = Cours("Cours de Musique", smith, L1info, 2)
c4.contraintes_salle.append(I416)

c5 = Cours("Cours de Cuisine", benoit16, BacProCuisine, 6)
c5.contraintes_salle.append(I417)

c6 = Cours("Cours de Maths", christ, BTSinfo, 2)
c7 = Cours("Cours de Musique", sinatra, BTSinfo, 4)
c7.contraintes_salle.append(I416)

c8 = Cours("Cours de Cuisine", sinatra, BacProCuisine, 1)
c8.contraintes_salle.append(I417)

c9 = Cours("Cours de Python", discala, L1info, 3)
c10 = Cours("Cours de Théâtre", smith, BTSinfo, 4)

c11 = Cours("Cours de Musique", sinatra, L1maths, 2)
c11.contraintes_salle.append(I416)

c12 = Cours("Cours de C#", discala, L1info, 4)
c13 = Cours("Cours d'Algèbre", dupont, BacProCuisine, 4)
cours = [c1,c2,c3,c4,c5,c6,c7,c8,c9,c10,c11,c12,c13]
for i,cr in enumerate(cours):
    cr.numero = i

#Génération des matrices pour la PLNE à partir de la modélisation
################################## CONVERSION EN MATRICES / EXECUTION DE LA PLNE / ON ACTUALISE NOS OBJETS AVEC LE RESULTAT ####################################################################

res = build_compute_plne(cours, creneaux, salles, classes, profs, demi_journees=demi_journees, penalite_cours_creneau_seul=1, max_time=200)

################################# AFFICHAGE ####################################################################################################################################################

afficher_profs = True
afficher_classes = True
afficher_salles = True

simple_print(demi_journees,profs,cours,salles,classes,afficher_profs,afficher_classes,afficher_salles,save_folder="./results/simple_example")

