from scipy.optimize import LinearConstraint
from scipy.optimize import Bounds
from scipy.optimize import milp
import numpy as np
from toolbox import Professeur,Classe,Salle
####################################################### MODELISATION EN FRANCAIS ########################################################################################

#### CONSTANTES ####
#cours_prof_classe(co, pr, cl) le cours co est tenu par le prof pr à la classe cl
#cours_pas_salle(co, sl) le cours ne peut pas avoir lieu dans la salle sl
#cours_pas_creneau(co, cr) le cours ne peut pas avoir lieu durant le créneau cr
#durée_cours(co) est la durée (en créneaux) du cours
#classe_mutex(cl1,cl2) les deux classes ne peuvent pas avoir cours en même temps (ex 2 groupes de TP de la même classe)

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
# 9] les classes qui ne peuvent pas avoir cours en même temps n'ont pas cours en même temps

#### PENALITÉS ####
# A] certains cours donnent une pénalité de 2 point si ils ont lieu durant un créneau
# B] on souhaite minimiser le nombre de jours qu'un prof (et donc qu'un cours) aura dans la semaine (1pt de pénalité par jour où le prof doit se rendre sur place)

### VARIABLE D'AIDE ####
# On définit la variable cours_commence_créneau(co, cr) qui représente le créneau de départ cr du cours co
# Cela donne la contrainte 6 pour lier les variables d'aides cours_commence_créneau à cours_créneau : si le cours co commence au créneau cr alors le cours a lieu aussi
# durant les créneaux qui suivent durant la durée du cours


######################################################## MODELISATION EN PLNE ##########################################################################################

# 1] Pour tout cours co, toute salle sl : si cours_pas_salle(co, sl) = 1 alors cours_salle(co, sl) <= 0
# 2] Pour tout cours co, tout créneau cr : si cours_pas_creneau(co, cr) = 1 alors cours_créneau(co, cr) <= 0
# 3] Pour tout cours co : (somme [cr dans CRENEAUX] cours_créneau(co, cr)) = durée_cours(co)
# 4] Pour chaque cours co1,co2, salle sl, cours_creneau(co1, cr) + cours_creneau(co2, cr) + cours_salle(co1, sl) + cours_salle(co2, sl) <= 3
# 5] Pour chaque cours co1,co2 qui ont le même prof, et tout créneau cr cours_creneau(co1, cr) + cours_creneau(co2, cr) <= 1
# 6.a] pour tout cours co, créneau cr, durée_cours(co) * cours_commence_créneau(co, cr) - (somme [créneaux cr2 qui suivent le créneau cr sur la durée du cours co] cours_creneau(co, cr2)) <= 0 (lie les cours au début du cours)
# 6.b] Pour tout cours co : somme[cr dans CRENAUX] cours_commence_créneau(co, cr) = 1 (un début de cours par cours)
# 7] Pour toute classe cl et tout créneau cr : somme [co les COURS concernant la classe cl] cours_créneau(co, cr) <= 1
# 8] Pour tout cours co : (somme [sl les SALLES] cours_salle(co, sl)) >= 1
######################################################## ON CREE NOTRE MODELISATION OBJET EN PYTHON ##########################################################################################

######################################################## PLNE EN PYTHON ##########################################################################################
def generate_milp(cours, creneaux, salles, classes):
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

    # 1] Pour tout cours co, toute salle sl : si cours_pas_salle(co, sl) = 1 alors cours_salle(co, sl) <= 0
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

    # 2] Pour tout cours co, tout créneau cr : si cours_pas_creneau(co, cr) = 1 alors cours_créneau(co, cr) <= 0
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

    # 4] Pour chaque cours co1,co2, salle sl : cours_creneau(co1, cr) + cours_creneau(co2, cr) + cours_salle(co1, sl) + cours_salle(co2, sl) <= 3
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

    # 5] Pour chaque cours co1,co2 qui ont le même prof, et tout créneau cr : cours_creneau(co1, cr) + cours_creneau(co2, cr) <= 1
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
    # durée_cours(co) * cours_commence_créneau(co, cr) - (somme [créneaux cr2 qui suivent le créneau cr sur la durée du cours co] cours_creneau(co, cr2)) <= 0
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

    # 9] Pour chaque cours co1,co2 qui sont mutex, et tout créneau cr : cours_creneau(co1, cr) + cours_creneau(co2, cr) <= 1
    for co1 in cours:
        for co2 in cours:
            if co1 in co2.classe.mutex:
                for cr in creneaux:
                    line_added = [0]*(nb_var_cours_creneau+nb_var_cours_salle+nb_var_commence+nb_var_penalites)
                    line_added[co1.numero*len(creneaux)+cr.numero] = 1
                    line_added[co2.numero*len(creneaux)+cr.numero] = 1
                    A.append(line_added)
                    UB.append(1)
                    LB.append(0)

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

    #Minimisation
    minimize = np.array([0]*(nb_var_cours_creneau+nb_var_cours_salle+nb_var_commence)+[1]*nb_var_penalites)


    return minimize,bounds,integrality,A,UB,LB,nb_var_cours_creneau,nb_var_cours_salle,nb_var_commence,nb_var_penalites