from scipy.optimize import LinearConstraint
from scipy.optimize import Bounds
from scipy.optimize import milp
import numpy as np

####################################################### MODELISATION EN FRANCAIS ########################################################################################

#### CONSTANTES ####
#cours_prof_classe(co, pr, cl) le cours co est tenu par le prof pr à la classe cl
#cours_pas_salle(co, sl) le cours ne peut pas avoir lieu dans la salle sl
#cours_pas_creneau(co, cr) le cours ne peut pas avoir lieu durant le créneau cr
#durée_cours(co) est la durée (en créneaux) du cours

#### VARIABLES ####
#cours_créneau(co, cr) signifie que le cours co a lieu durant le créneau cr
#cours_salle(co, sl) signifie que le cours co a lieu dans la salle sl

#### CONTRAINTES ####
# 1] certains cours ne peuvent pas avoir lieu sur certains crénaux (disponibilité du prof)
# 2] certains cours doivent avoir lieu dans un groupe de salle en raison de la disponibilité du materiel
# 3] la durée d'un cours dans la semaine est bien la bonne
# 4] 2 cours ne peuvent pas avoir lieu dans la même salle au même moment
# 5] 2 cours tenus par le même prof ne peuvent pas se chevaucher
# 6] un cours a lieu durant des créneaux consécutifs
# 7] une classe ne peut pas avoir 2 cours en même temps
# 8] chaque cours a bien une salle

#### PENALITÉS ####
# A] certains cours donnent une pénalité de 2 point si ils ont lieu durant un créneau
# B] on souhaite minimiser le nombre de jours qu'un prof (et donc qu'un cours) aura dans la semaine (1pt de pénalité par jour où le prof doit se rendre sur place)

### VARIABLE D'AIDE ####
# On définit la variable cours_commence_créneau(co, cr) qui représente le créneau de départ cr du cours co
# Cela donne la contrainte 6 pour lier les variables d'aides cours_commence_créneau à cours_créneau : si le cours co commence au créneau cr alors le cours a lieu aussi
# durant les créneaux qui suivent durant la durée du cours


######################################################## MODELISATION EN PLNE ##########################################################################################

# 1] Pour tous les cours co : si cours_pas_salle(co, sl) = 1 alors cours_salle(co, cr) <= 0
# 2] Pour tous les cours co : si cours_pas_creneau(co, cr) = 1 alors cours_créneau(co, cr) <= 0
# 3] Pour tous les cours co : (somme [cr dans CRENEAUX] cours_créneau(co, cr)) = durée_cours(co)
# 4] Pour chaque cours co1,co2, salle sl, cours_creneau(co1, cr) + cours_creneau(co2, cr) + cours_salle(co1, sl) + cours_salle(co2, sl) <= 3
# 5] Pour chaque cours co1,co2 qui ont le même prof, et tout créneau cr cours_creneau(co1, cr) + cours_creneau(co2, cr) <= 1
# 6.a] pour tout cours co, créneau cr, durée_cours(co) * cours_commence_créneau(co, cr) - (somme [créneaux cr qui suivent durant la durée du cours co] cours_creneau(co, cr)) <= 0 (lie les cours au début du cours)
# 6.b] Pour tout cours co : somme[cr dans CRENAUX] cours_commence_créneau(co, cr) = 1 (un début de cours par cours)
# 7] Pour toute classe cl et tout créneau cr : somme [co les COURS concernant la classe cl] cours_créneau(co, cr) <= 1
# 8] Pour tout cours co : (somme [sl les SALLES] cours_salle(co, sl)) >= 1
######################################################## ON CREE NOTRE MODELISATION OBJET EN PYTHON ##########################################################################################

#8 créneaux par demi-journée
duree_demi_journee = 8
nombre_demi_journees = 3

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

#RAPPEL DES CONSTANTES
#cours_prof(co, pr) le cours co est tenu par le prof pr
#cours_pas_salle(co, sl) le cours ne peut pas avoir lieu dans la salle sl
#cours_pas_creneau(co, cr) le cours ne peut pas avoir lieu durant le créneau cr
#durée_cours(co) est la durée (en créneaux) du cours

#définition des classes
class Classe:
    def __init__(self, niveau, spe):
        self.niveau = niveau
        self.spe = spe

#définition des salles
class Salle:
    def __init__(self, batiment, etage, salle):
        self.batiment = batiment
        self.etage = etage
        self.salle = salle
        self.numero = -1

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
        self.contraintes_pas_salle = [] #Contraintes des salles dans lesquelles ce cours ne peut pas avoir lieu
        self.numero = -1
        self.organisation = None

    def set_organisation(self, creneaux, salle):
        self.organisation = self.Organisation(creneaux, salle)

#définition des professeurs
class Professeur:
    def __init__(self, nom, prenom):
        self.nom = nom
        self.prenom = prenom
        self.contraintes_pas_cours = [] #Contraintes des créneaux durant lesquelles ce prof ne peut pas venir
        self.contraintes_pref_pas_cours = [] #Tuple (Contraintes des créneaux durant lesquelles ce prof ne veut pas venir, pénalité)


######################################################## ON CREE UN EXEMPLE ##########################################################################################

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
    discala.contraintes_pref_pas_cours.append(demi_journees[1][i]) #pas cours la deuxième mi-journée (contrainte de pénalité)
dupont = Professeur("DUPONT", "Martin")

smith = Professeur("SMITH", "Will")
for i in range(4):
    smith.contraintes_pas_cours.append(demi_journees[1][2+i]) #pas cours au milieu de la deuxième mi-journée
for i in range(8):
    smith.contraintes_pref_pas_cours.append(demi_journees[1][i]) #pas cours la deuxième mi-journée (contrainte de pénalité)
benoit16 = Professeur("16", "Benoit")

christ = Professeur("CHRIST", "Jésus")

sinatra = Professeur("SINATRA", "Frank")
for i in range(8):
    sinatra.contraintes_pas_cours.append(demi_journees[1][i]) #pas cours la deuxième demi-journée

profs = [discala, dupont, smith, benoit16, christ, sinatra]

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
classes = [L1info, L1maths, BTSinfo, BacProCuisine]

#définition des cours
c1 = Cours("Cours de Python", discala, L1info, 4)
c2 = Cours("Cours de Stats", dupont, L1maths, 4)
c3 = Cours("Cours d'Algèbre", dupont, L1maths, 6)
c4 = Cours("Cours de Musique", smith, L1info, 2)
c4.contraintes_pas_salle.append(I415)
c4.contraintes_pas_salle.append(I417)

c5 = Cours("Cours de Cuisine", benoit16, BacProCuisine, 6)
c5.contraintes_pas_salle.append(I415)
c5.contraintes_pas_salle.append(I416)

c6 = Cours("Cours de Maths", christ, BTSinfo, 2)
c7 = Cours("Cours de Musique", sinatra, BTSinfo, 4)
c7.contraintes_pas_salle.append(I415)
c7.contraintes_pas_salle.append(I417)

c8 = Cours("Cours de Cuisine", sinatra, BacProCuisine, 1)
c8.contraintes_pas_salle.append(I415)
c8.contraintes_pas_salle.append(I416)

c9 = Cours("Cours de Python", discala, L1info, 3)
c10 = Cours("Cours de Théâtre", smith, BTSinfo, 4)

c11 = Cours("Cours de Musique", sinatra, L1maths, 2)
c11.contraintes_pas_salle.append(I415)
c11.contraintes_pas_salle.append(I417)

c12 = Cours("Cours de C#", discala, L1info, 4)
c13 = Cours("Cours de d'Algèbre", dupont, BacProCuisine, 4)
cours = [c1,c2,c3,c4,c5,c6,c7,c8,c9,c10,c11,c12,c13]
for i,cr in enumerate(cours):
    cr.numero = i

######################################################## CONTRAINTES DEPUIS NOTRE EXEMPLE ##########################################################################################
integrality = []
nb_var_cours_creneau = 0
nb_var_cours_salle = 0
nb_var_commence = 0
nb_var_penalites = 0
#Rappel des variables
#cours_créneau(co, cr) signifie que le cours co a lieu durant le créneau cr
for co in cours:
    for cr in creneaux:
        integrality.append(1)
        nb_var_cours_creneau += 1
#cours_salle(co, sl) signifie que le cours co a lieu dans la salle sl
for co in cours:
    for sl in salles:
        integrality.append(1)
        nb_var_cours_salle += 1
#cours_commence_créneau(co, cr) signifie que le cours co a lieu durant le créneau cr
for co in cours:
    for cr in creneaux:
        integrality.append(1)
        nb_var_commence += 1
#variables de pénalités
for co in cours:
    for cr in creneaux:
        integrality.append(1)
        nb_var_penalites += 1
bounds = Bounds([0]*(nb_var_cours_creneau+nb_var_cours_salle+nb_var_commence+nb_var_penalites), [1]*(nb_var_cours_creneau+nb_var_cours_salle+nb_var_commence)+[np.inf]*(nb_var_penalites))

A = []
UB = []
LB = []


# 1] Pour tous les cours co : si cours_pas_salle(co, sl) = 1 alors cours_salle(co, cr) <= 0
i=0
for co in cours:
    for sl in salles:
        if sl in co.contraintes_pas_salle:
            line_added = [0]*(nb_var_cours_creneau+nb_var_cours_salle+nb_var_commence+nb_var_penalites)
            line_added[i+nb_var_cours_creneau] = 1
            A.append(line_added)
            UB.append(0)
            LB.append(-np.inf)
        i+=1

# 2] Pour tous les cours co, creneau cr : si cours_pas_creneau(co, cr) = 1 alors cours_créneau(co, cr) <= 0
i=0
for co in cours:
    for cr in creneaux:
        if cr in co.prof.contraintes_pas_cours:
            line_added = [0]*(nb_var_cours_creneau+nb_var_cours_salle+nb_var_commence+nb_var_penalites)
            line_added[co.numero*len(creneaux)+cr.numero] = 1
            A.append(line_added)
            UB.append(0)
            LB.append(-np.inf)
        i+=1

# 3] Pour tous les cours co : (somme [cr dans CRENEAUX] cours_créneau(co, cr)) = durée_cours(co)
for co in cours:
    line_added = [0]*(nb_var_cours_creneau+nb_var_cours_salle+nb_var_commence+nb_var_penalites)
    for cr in creneaux:
        line_added[co.numero*len(creneaux)+cr.numero] = 1
    A.append(line_added)
    UB.append(co.duree)
    LB.append(co.duree)

# 4] Pour chaque cours co1,co2, salle sl, cours_creneau(co1, cr) + cours_creneau(co2, cr) + cours_salle(co1, sl) + cours_salle(co2, sl) <= 3
for co1 in cours:
    for co2 in cours:
        if co1 != co2:
            for sl in salles:
                for cr in creneaux:
                    line_added = [0]*(nb_var_cours_creneau+nb_var_cours_salle+nb_var_commence+nb_var_penalites)
                    line_added[co1.numero*len(creneaux)+cr.numero] = 1
                    line_added[co2.numero*len(creneaux)+cr.numero] = 1
                    line_added[nb_var_cours_creneau + co1.numero*len(salles)+sl.numero] = 1
                    line_added[nb_var_cours_creneau + co2.numero*len(salles)+sl.numero] = 1
                    A.append(line_added)
                    UB.append(3)
                    LB.append(0)

# 5] Pour chaque cours co1,co2 qui ont le même prof, et tout créneau cr cours_creneau(co1, cr) + cours_creneau(co2, cr) <= 1
for co1 in cours:
    for co2 in cours:
        if co1 != co2 and co1.prof == co2.prof:
            for cr in creneaux:
                line_added = [0]*(nb_var_cours_creneau+nb_var_cours_salle+nb_var_commence+nb_var_penalites)
                line_added[co1.numero*len(creneaux)+cr.numero] = 1
                line_added[co2.numero*len(creneaux)+cr.numero] = 1
                A.append(line_added)
                UB.append(1)
                LB.append(0)

# 6.a] pour tout cours co, créneau cr,
# durée_cours(co) * cours_commence_créneau(co, cr) - (somme [créneaux cr qui suivent durant la durée du cours co] cours_creneau(co, cr)) <= 0
for co in cours:
    for cr in creneaux:

        suivants = cr.get_suivants()[:co.duree]
        line_added = [0]*(nb_var_cours_creneau+nb_var_cours_salle+nb_var_commence+nb_var_penalites)
        
        line_added[nb_var_cours_creneau+nb_var_cours_salle+co.numero*len(creneaux)+cr.numero] = co.duree
        for cr2 in suivants:
            line_added[co.numero*len(creneaux)+cr2.numero] = -1

        A.append(line_added)
        UB.append(0)
        LB.append(-np.inf)

# 6.b] Pour tout cours co : somme[cr dans CRENAUX] cours_commence_créneau(co, cr) = 1
for co in cours:
    line_added = [0]*(nb_var_cours_creneau+nb_var_cours_salle+nb_var_commence+nb_var_penalites)
    for cr in creneaux:
        line_added[nb_var_cours_creneau+nb_var_cours_salle + cr.numero+co.numero*len(creneaux)] = 1
    A.append(line_added)
    UB.append(1)
    LB.append(1)

# 7] Pour toute classe cl et tout créneau cr : somme [co les COURS concernant la classe cl] cours_créneau(co, cr) <= 1
for cl in classes:
    for cr in creneaux:
        line_added = [0]*(nb_var_cours_creneau+nb_var_cours_salle+nb_var_commence+nb_var_penalites)
        for co in cours:
            if co.classe == cl:
                line_added[cr.numero+co.numero*len(creneaux)] = 1
        A.append(line_added)
        UB.append(1)
        LB.append(-np.inf)


# 8] Pour tout cours co : (somme [sl les SALLES] cours_salle(co, sl)) = 1
for co in cours:
    line_added = [0]*(nb_var_cours_creneau+nb_var_cours_salle+nb_var_commence+nb_var_penalites)
    for sl in salles:
        line_added[nb_var_cours_creneau + sl.numero+co.numero*len(salles)] = 1
    A.append(line_added)
    UB.append(1)
    LB.append(1)

# A] certains cours donnent une pénalité de k point si ils ont lieu durant un créneau
# pour chaque cours : pénalité(co,cr) = (somme [cr dans creneaux] cours_creneau(co,cr)) * pénalité (2 ici)
i=0
for co in cours:
    for cr in creneaux:
        if cr in co.prof.contraintes_pref_pas_cours:
            line_added = [0]*(nb_var_cours_creneau+nb_var_cours_salle+nb_var_commence+nb_var_penalites)
            line_added[nb_var_cours_creneau+nb_var_cours_salle+nb_var_commence+co.numero*len(creneaux)+cr.numero] = 1
            line_added[co.numero*len(creneaux)+cr.numero] = -2
            A.append(line_added)
            UB.append(0)
            LB.append(0)
        i+=1


#############################################################################################

print("Nb contraintes : ",len(A))
print("Nb variables : ",len(A[0]))

minimize = np.array([0]*(nb_var_cours_creneau+nb_var_cours_salle+nb_var_commence)+[1]*nb_var_penalites)

constraints = LinearConstraint(A,ub=UB,lb=LB)
res = milp(c=minimize, bounds=bounds, constraints=constraints, integrality=integrality)

if res.status != 0:
    print("Impossible de trouver un résultat avec ces contraintes")
    exit(1)
else:
    print("Solution trouvée avec un score de",res.fun)
################################# ON ACTUALISE NOS OBJETS AVEC LE RESULTAT #################################################

i = 0
#Affectations cours-creneaux
for co in cours:
    creneaux_co = []
    for cr in creneaux:
        if res.x[i]:
            creneaux_co.append(cr)
        i += 1
    co.set_organisation(creneaux_co,None)
#Affectations cours-salles
for co in cours:
    for sl in salles:
        if res.x[i]:
            co.organisation.salle = sl
        i += 1

################################# AFFICHAGE #################################################

afficher_profs = True
afficher_classes = True
afficher_salles = True

#Affichage par prof
if afficher_profs:
    for prof in profs:
        print()
        print("==================================================")
        print()
        print("Emploi du temps de",prof.prenom,prof.nom)
        for dj_n,dj in enumerate(demi_journees):
            print("demi-journée",dj_n+1," :::::::::::::::")
            for cr_n,cr in enumerate(dj):
                found = False
                for co in cours:
                    if co.prof != prof:
                        continue
                    if cr in co.organisation.creneaux:
                        found = True
                        if cr in prof.contraintes_pref_pas_cours:
                            print(str((cr_n+1)/2)+"h [2] -",co.nom,"["+co.organisation.salle.batiment+str(co.organisation.salle.etage)+str(co.organisation.salle.salle)+"]","("+co.classe.niveau+" "+co.classe.spe+")")
                        else:
                            print(str((cr_n+1)/2)+"h -",co.nom,"["+co.organisation.salle.batiment+str(co.organisation.salle.etage)+str(co.organisation.salle.salle)+"]","("+co.classe.niveau+" "+co.classe.spe+")")
                if cr in prof.contraintes_pas_cours:
                    print(str((cr_n+1)/2)+"h [x] -")
                elif cr in prof.contraintes_pref_pas_cours and not found:
                    print(str((cr_n+1)/2)+"h [2] -")
                elif not found:
                    print(str((cr_n+1)/2)+"h -")

#Affichage par classe
if afficher_classes:
    for cl in classes:
        print()
        print("==================================================")
        print()
        print("Emploi du temps de",cl.niveau,cl.spe)
        for dj_n,dj in enumerate(demi_journees):
            print("demi-journée",dj_n+1," :::::::::::::::")
            for cr_n,cr in enumerate(dj):
                found = False
                for co in cours:
                    if co.classe != cl:
                        continue
                    if cr in co.organisation.creneaux:
                        found = True
                        print(str((cr_n+1)/2)+"h -",co.nom,"["+co.organisation.salle.batiment+str(co.organisation.salle.etage)+str(co.organisation.salle.salle)+"]","("+co.prof.prenom,co.prof.nom+")")
                if not found:
                    print(str((cr_n+1)/2)+"h -")


#Affichage par salle
if afficher_salles:
    for sl in salles:
        print()
        print("==================================================")
        print()
        print("Emploi du temps de",sl.batiment+str(sl.etage)+str(sl.salle))
        for dj_n,dj in enumerate(demi_journees):
            print("demi-journée",dj_n+1," :::::::::::::::")
            for cr_n,cr in enumerate(dj):
                found = False
                for co in cours:
                    if co.organisation.salle != sl:
                        continue
                    if cr in co.organisation.creneaux:
                        found = True
                        print(str((cr_n+1)/2)+"h -",co.nom,"["+co.prof.prenom,co.prof.nom+"]","("+co.classe.niveau+" "+co.classe.spe+")")
                if not found:
                    print(str((cr_n+1)/2)+"h -")