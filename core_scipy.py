from scipy.optimize import LinearConstraint
from scipy.optimize import Bounds
from scipy.optimize import milp,linprog
import numpy as np
from toolbox import Professeur,Classe,Salle
import os
from scipy.sparse import csr_matrix,lil_matrix,vstack
from time import time
####################################################### MODELISATION EN FRANCAIS ########################################################################################

#### CONSTANTES ####
#cours_prof_classe(co, pr, cl) le cours co est tenu par le prof pr à la classe cl
#cours_doit_salle(co, sl) le cours doit avoir lieu dans une des salles sl
#cours_pas_creneau(co, cr) le cours ne peut pas avoir lieu durant le créneau cr
#durée_cours(co) est la durée (en créneaux) du cours
#classe_mutex(cl1,cl2) les deux classes ne peuvent pas avoir cours en même temps (ex 2 groupes de TP de la même classe)

#### VARIABLES ####
#cours_créneau(co, cr) signifie que le cours co a lieu durant le créneau cr
#cours_salle(co, sl) signifie que le cours co a lieu dans la salle sl
#cours_demi_journee(pr, dj) signifie que le prof a cours durant une demi-journée

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
# 10] les cours qui ne peuvent être que sur certains créneaux sont placé sur ces créneaux
# 11] la taille de la salle de cours est > taille de la classe qui y a cours
# 12] cours_salle_creneau(co, sl, cr) est à 1 si le cours est dans cette salle durant ce créneau
# 13] cours_demi_journee(pr, dj) est à 1 si le prof a cours dans la demi-journée

#### PENALITÉS ####
# A] certains cours donnent une pénalité de 2 point si ils ont lieu durant un créneau
# B] on souhaite minimiser le nombre de jours qu'un prof (et donc qu'un cours) aura dans la semaine (1pt de pénalité par jour où le prof doit se rendre sur place)
# C] on apporte un bonus quand le prof a une salle qu'il veut avoir
# D] on souhaite minimiser le nombre cours "seuls" (sans aucun voisin) pour tous les profs dans la semaine

### VARIABLE D'AIDE ####
# On définit la variable cours_commence_créneau(co, cr) qui représente le créneau de départ cr du cours co
# Cela donne la contrainte 6 pour lier les variables d'aides cours_commence_créneau à cours_créneau : si le cours co commence au créneau cr alors le cours a lieu aussi
# durant les créneaux qui suivent durant la durée du cours


######################################################## MODELISATION EN PLNE ##########################################################################################

# 1] Pour tout cours co : somme [salle sl tq cours_doit_salle(co, sl)] >= 1
# 2] Pour tout cours co, tout créneau cr : si cours_pas_creneau(co, cr) = 1 alors cours_créneau(co, cr) <= 0
# 3] Pour tout cours co : (somme [cr dans CRENEAUX] cours_créneau(co, cr)) = durée_cours(co)
# 4] Pour chaque cours co1,co2, salle sl, cours_creneau(co1, cr) + cours_creneau(co2, cr) + cours_salle(co1, sl) + cours_salle(co2, sl) <= 3
# 5] Pour chaque cours co1,co2 qui ont le même prof, et tout créneau cr cours_creneau(co1, cr) + cours_creneau(co2, cr) <= 1
# 6.a] pour tout cours co, créneau cr, durée_cours(co) * cours_commence_créneau(co, cr) - (somme [créneaux cr2 qui suivent le créneau cr sur la durée du cours co] cours_creneau(co, cr2)) <= 0 (lie les cours au début du cours)
# 6.b] Pour tout cours co : somme[cr dans CRENAUX] cours_commence_créneau(co, cr) = 1 (un début de cours par cours)
# 7] Pour toute classe cl et tout créneau cr : somme [co les COURS concernant la classe cl] cours_créneau(co, cr) <= 1
# 8] Pour tout cours co : (somme [sl les SALLES] cours_salle(co, sl)) >= 1
# 9] Pour chaque cours co1,co2 qui sont mutex, et tout créneau cr : cours_creneau(co1, cr) + cours_creneau(co2, cr) <= 1
# 10] Pour chaque cours co qui est contraint par des créneaux, pour tout créneau cr, si cr n'est pas dans les contraintes alors cours_creneau(co, cr) <= 0
# 11] Pour tout cours co, tout créneau cr, toute salle sl : cours_salle(co, sl)*taille(classe(co)) <= taille(sl)
# 12] Pour tout cours co, salle sl, créneau cr, cours_creneau(co, cr) + cours_salle(co, sl) - cours_salle_creneau(co, sl, cr) <= 1 (cours_creneau(co, cr) et cours_salle(co, sl) => cours_salle_creneau(co, sl, cr))
# 13] Pour toutes les demi-journées dj, pour tous les profs pj, pour tous les créneaux cr dans dj, tous les cours co dans COURS du prof, cours_creneau(co, cr)) <= cours_demi_journee(pr, dj)
######################################################## ON CREE NOTRE MODELISATION OBJET EN PYTHON ##########################################################################################

######################################################## PLNE EN PYTHON ##########################################################################################
def generate_milp(cours, creneaux, salles, classes, profs, demi_journees=None, verbose=False, penalite_cours_creneau_seul=1, penalite_journee_travaillee=10):
    integrality = []
    nb_var_cours_creneau = 0
    nb_var_cours_salle = 0
    nb_var_commence = 0
    nb_var_salle_affec = 0
    nb_var_cours_journee = 0
    nb_var_cours_seul = 0

    #Rappel des variables
    #cours_créneau(co, cr) signifie que le cours co a lieu durant le créneau cr
    if verbose:
        print("génération de l'intégralité")
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
    #cours_salle_creneau(co, sl, cr) = le cours est dans cette salle durant ce créneau
    for sl in salles:
        for cr in creneaux:
            for co in cours:
                integrality.append(1)
                nb_var_salle_affec += 1

    nb_var = nb_var_cours_creneau+nb_var_cours_salle+nb_var_commence+nb_var_salle_affec

    #creneau_seul(pr, cr) = le prof préfère ne pas avoir cours dans le créneau car il est seul
    if demi_journees != None:
        demi_journees = [(i,dj) for i,dj in enumerate(demi_journees)]
        
        
        if penalite_cours_creneau_seul != 0:
            for pr in profs:
                for cr in creneaux:
                    integrality.append(1)
                    nb_var_cours_seul += 1
            nb_var += nb_var_cours_seul

        journees = []
        for dj in demi_journees:
            if dj[0]%2 == 0:
                journees.append([dj])
            else:
                journees[-1].append(dj)
            
    #cours_journee(pr, dj) = le prof a cours durant la journee dj
        for pr in profs:
            for dj in journees:
                integrality.append(1)
                nb_var_cours_journee += 1
        nb_var += nb_var_cours_journee

    
    if verbose:
        print("génération des limites")
    bounds = Bounds(np.zeros(nb_var), np.ones(nb_var))
    
    if verbose:
        print("nombre de variables :",nb_var)
    A = []
    UB = []
    LB = []

    # 1] Pour tout cours co : somme [salle sl tq cours_doit_salle(co, sl)] >= 1
    if verbose:
        print("génération contrainte 1")

    for co in cours:
        if len(co.contraintes_salle) > 0:
            line_added = np.zeros(nb_var)
            for sl in co.contraintes_salle:
                line_added[nb_var_cours_creneau + co.numero*len(salles)+sl.numero] = 1
            A.append(csr_matrix(line_added))
            UB.append(np.inf)
            LB.append(1)

    # 2] Pour tout cours co, tout créneau cr : si cours_pas_creneau(co, cr) = 1 alors cours_créneau(co, cr) <= 0
    if verbose:
        print("génération contrainte 2")
    for co in cours:
        for cr in creneaux:
            if co.prof != None and cr in co.prof.contraintes_pas_cours:
                line_added = np.zeros(nb_var)
                line_added[co.numero*len(creneaux)+cr.numero] = 1
                A.append(csr_matrix(line_added))
                UB.append(0)
                LB.append(-np.inf)

    # 3] Pour tous les cours co : (somme [cr dans CRENEAUX] cours_créneau(co, cr)) = durée_cours(co)
    if verbose:
        print("génération contrainte 3")
    for co in cours:
        line_added = np.zeros(nb_var)
        for cr in creneaux:
            line_added[co.numero*len(creneaux)+cr.numero] = 1
        A.append(csr_matrix(line_added))
        UB.append(co.duree)
        LB.append(co.duree)

    # 4] Pour toute salle sl, creneau cr, somme [co dans COURS] cours_salle_creneau(co,sl,cr) <= 1
    if verbose:
        print("génération contrainte 4")
        for sl in salles:
            for cr in creneaux:
                line_added = np.zeros(nb_var)
                for co in cours:
                    line_added[nb_var_cours_creneau + nb_var_cours_salle + nb_var_commence + co.numero*len(salles)*len(creneaux) + sl.numero*len(creneaux) + cr.numero] = 1
                A.append(csr_matrix(line_added))
                UB.append(1)
                LB.append(-np.inf)

    # 5] Pour chaque cours co1,co2 qui ont le même prof, et tout créneau cr : cours_creneau(co1, cr) + cours_creneau(co2, cr) <= 1
    if verbose:
        print("génération contrainte 5")
    c_done = []
    for co1 in cours:
        c_done.append(co1)
        for co2 in cours:
            if (co1.prof != None) and (co2.prof != None) and (not co2 in c_done) and co1.prof is co2.prof:
                for cr in creneaux:
                    line_added = np.zeros(nb_var)
                    line_added[co1.numero*len(creneaux)+cr.numero] = 1
                    line_added[co2.numero*len(creneaux)+cr.numero] = 1
                    A.append(csr_matrix(line_added))
                    UB.append(1)
                    LB.append(-np.inf)
        

    # 6.a] pour tout cours co, créneau cr,
    # durée_cours(co) * cours_commence_créneau(co, cr) - (somme [créneaux cr2 qui suivent le créneau cr sur la durée du cours co] cours_creneau(co, cr2)) <= 0
    if verbose:
        print("génération contrainte 6a")
    for co in cours:
        for cr in creneaux:

            suivants = cr.get_suivants()[:co.duree]
            line_added = np.zeros(nb_var)
            
            line_added[nb_var_cours_creneau+nb_var_cours_salle+co.numero*len(creneaux)+cr.numero] = co.duree
            for cr2 in suivants:
                line_added[co.numero*len(creneaux)+cr2.numero] = -1

            A.append(csr_matrix(line_added))
            UB.append(0)
            LB.append(-np.inf)

    # 6.b] Pour tout cours co : somme[cr dans CRENAUX] cours_commence_créneau(co, cr) = 1
    if verbose:
        print("génération contrainte 6b")
    for co in cours:
        line_added = np.zeros(nb_var)
        for cr in creneaux:
            line_added[nb_var_cours_creneau+nb_var_cours_salle + cr.numero+co.numero*len(creneaux)] = 1
        A.append(csr_matrix(line_added))
        UB.append(1)
        LB.append(1)

    # 7] Pour toute classe cl et tout créneau cr : somme [co les COURS concernant la classe cl] cours_créneau(co, cr) <= 1
    if verbose:
        print("génération contrainte 7")
    for cl in classes:
        for cr in creneaux:
            line_added = np.zeros(nb_var)
            for co in cours:
                if co.classe is cl:
                    line_added[cr.numero+co.numero*len(creneaux)] = 1
            A.append(csr_matrix(line_added))
            UB.append(1)
            LB.append(-np.inf)


    # 8] Pour tout cours co : (somme [sl les SALLES] cours_salle(co, sl)) = 1
    if verbose:
        print("génération contrainte 8")
    for co in cours:
        line_added = np.zeros(nb_var)
        for sl in salles:
            line_added[nb_var_cours_creneau + sl.numero+co.numero*len(salles)] = 1
        A.append(csr_matrix(line_added))
        UB.append(1)
        LB.append(1)

    # 9] Pour chaque cours co1,co2 qui sont mutex, et tout créneau cr : cours_creneau(co1, cr) + cours_creneau(co2, cr) <= 1
    if verbose:
        print("génération contrainte 9")
    for co1 in cours:
        for co2 in cours:
            if co2.classe in co1.classe.mutex:
                for cr in creneaux:
                    line_added = np.zeros(nb_var)
                    line_added[co1.numero*len(creneaux)+cr.numero] = 1
                    line_added[co2.numero*len(creneaux)+cr.numero] = 1
                    A.append(csr_matrix(line_added))
                    UB.append(1)
                    LB.append(-np.inf)

    # 10] Pour chaque cours co qui est contraint par des créneaux, pour tout créneau cr, si cr n'est pas dans les contraintes alors cours_creneau(co, cr) <= 0
    if verbose:
        print("génération contrainte 10")
    for co in cours:
        if len(co.contrainte_dans_creneaux) > 0:
            for cr in creneaux:
                if not cr in co.contrainte_dans_creneaux:
                    line_added = np.zeros(nb_var)
                    line_added[co.numero*len(creneaux)+cr.numero] = 1
                    A.append(csr_matrix(line_added))
                    UB.append(0)
                    LB.append(-np.inf)

    # 11] Pour tout cours co, toute salle sl : cours_salle(co, sl)*taille(classe(co)) <= taille(sl)
    if verbose:
        print("génération contrainte 11")
    for co in cours:
        for sl in salles:
            if (not np.isinf(sl.effectifs)) and co.classe.effectifs > 0:
                line_added = np.zeros(nb_var)
                line_added[nb_var_cours_creneau + co.numero*len(salles)+sl.numero] = co.classe.effectifs
                A.append(csr_matrix(line_added))
                UB.append(sl.effectifs)
                LB.append(-np.inf)

    # 12] cours_salle_creneau(co, sl, cr) doit être 1 si jamais il y a le cours co dans le créneau cr dans la salle sl
    # pour tout cours co, salle sl, créneau cr, cours_creneau(co, cr) + cours_salle(co, sl) - cours_salle_creneau(co, sl, cr) <= 1 (cours_creneau(co, cr) et cours_salle(co, sl) => cours_salle_creneau(co, sl, cr))
    if verbose:
        print("génération contrainte 12")
    for co in cours:
        for cr in creneaux:
            for sl in salles:
                line_added = np.zeros(nb_var)
                line_added[co.numero*len(creneaux)+cr.numero] = 1
                line_added[nb_var_cours_creneau + co.numero*len(salles)+sl.numero] = 1
                line_added[nb_var_cours_creneau + nb_var_cours_salle + nb_var_commence + co.numero*len(salles)*len(creneaux) + sl.numero*len(creneaux) + cr.numero] = -1
                A.append(csr_matrix(line_added))
                UB.append(1)
                LB.append(-np.inf)

    # 13a] Pour toutes les journées j, pour tous les profs pr, pour tous les créneaux cr dans j, tous les cours co dans COURS du prof, cours_creneau(co, cr) - cours_journee(pr, j) <= 0
    if demi_journees != None:
        if verbose:
            print("génération contrainte 13a")
        for i,j in enumerate(journees):
            for i_2,dj in j:
                for cr in dj:
                    for pr in profs:
                        for co in cours:
                            if co.prof is pr:
                                line_added = np.zeros(nb_var)
                                line_added[co.numero*len(creneaux)+cr.numero] = 1
                                line_added[nb_var_cours_creneau+nb_var_cours_salle+nb_var_commence+nb_var_salle_affec + pr.numero * len(journees) + i] = -1
                                A.append(csr_matrix(line_added))
                                UB.append(0)
                                LB.append(-np.inf)


    # 13b] Pour tous les créneaux cr, pour tous les profs pr : (somme[co in Cours du Prof] cours_creneau(co,cr-1)) + (somme[co in Cours du Prof] cours_creneau(co,cr+1)) + 2*creneau_a_eviter(pr,cr) >= 2  

    if penalite_cours_creneau_seul != 0 and demi_journees != None:
        if verbose:
            print("génération contrainte 13b.v2")
        for cr in creneaux:
            for i,dj in demi_journees:
                if cr in dj:
                    demi_journee_cr = i
            for pr in profs:
                line_added = np.zeros(nb_var)
                
                done1=False
                if len(creneaux) > cr.numero+1:
                    cr_suivant = creneaux[cr.numero+1]
                    for i,dj in demi_journees:
                        if cr_suivant in dj:
                            demi_journee_cr_suivant = i
                    if (demi_journee_cr_suivant == demi_journee_cr) or (demi_journee_cr_suivant == demi_journee_cr+1 and demi_journee_cr%2 == 0):
                        done1 = True
                        for co in cours:
                            if co.prof is pr:
                                line_added[co.numero*len(creneaux)+cr_suivant.numero] = 1
                done2=False
                if 0 <= cr.numero-1:
                    cr_precedent = creneaux[cr.numero-1]
                    for i,dj in demi_journees:
                        if cr_precedent in dj:
                            demi_journee_cr_precedent = i
                    if (demi_journee_cr_precedent == demi_journee_cr) or (demi_journee_cr_precedent == demi_journee_cr-1 and demi_journee_cr%2 == 1):
                        done2 = True
                        for co in cours:
                            if co.prof is pr:
                                line_added[co.numero*len(creneaux)+cr_precedent.numero] = 1

                if (not done1) or (not done2):
                    line_added[nb_var_cours_creneau+nb_var_cours_salle+nb_var_commence+nb_var_salle_affec+nb_var_cours_journee+pr.numero*len(creneaux)+cr.numero] = 1
                else:
                    line_added[nb_var_cours_creneau+nb_var_cours_salle+nb_var_commence+nb_var_salle_affec+nb_var_cours_journee+pr.numero*len(creneaux)+cr.numero] = 2

                A.append(csr_matrix(line_added))
                UB.append(np.inf)
                if (not done1) or (not done2):
                    LB.append(1)
                else:
                    LB.append(2)

    #Objectif
    minimize = np.zeros(nb_var)

    # A] certains cours donnent une pénalité de k point si ils ont lieu durant un créneau
    # pour chaque cours : pénalité(co,cr) = (somme [cr dans creneaux] cours_creneau(co,cr)) * pénalité (2 ici)
    if verbose:
        print("génération des préférences")
    
    #pénalité préférences pas cours prof
    for co in cours:
        if co.prof != None:
            for cr in co.prof.contraintes_pref_pas_cours:
                minimize[co.numero*len(creneaux)+cr.numero] += co.prof.contraintes_pref_pas_cours[cr]

    #B] pénalité cours dans mauvaise salle
    for co in cours:
        for sl in salles:
            minimize[nb_var_cours_creneau + co.numero*len(salles)+sl.numero] += sl.penalite_salle

    #C] bonus si prof a cours dans une salle qu'il aime
    #pénalité
    for co in cours:
        if co.prof != None:
            for sl in co.prof.bonus_salle:
                minimize[nb_var_cours_creneau + co.numero*len(salles)+sl.numero] -= co.prof.bonus_salle[sl]

    #D] 1] pénalités pour les créneaux seuls 2] pénalité du nombre de journées travaillées par les profs
    if demi_journees != None:
        if penalite_cours_creneau_seul != 0:
            minimize[nb_var_cours_creneau+nb_var_cours_salle+nb_var_commence+nb_var_salle_affec+nb_var_cours_journee:] = penalite_cours_creneau_seul
        minimize[nb_var_cours_creneau+nb_var_cours_salle+nb_var_commence+nb_var_salle_affec:nb_var_cours_creneau+nb_var_cours_salle+nb_var_commence+nb_var_salle_affec+nb_var_cours_journee] = penalite_journee_travaillee

    return minimize,bounds,integrality,vstack(A),UB,LB,nb_var_cours_creneau,nb_var_cours_salle,nb_var_commence,nb_var_salle_affec,nb_var_cours_seul,nb_var_cours_journee,journees

def refresh_objects_with_result(res, cours, creneaux, salles):
    if not res.status in [0,1,4]:
        raise RuntimeError("Aucune solution trouvée pour ce problème !")
    i = 0
    #Affectations cours-creneaux
    for co in cours:
        creneaux_co = []
        for cr in creneaux:
            if res.x[i] > 0.5:
                creneaux_co.append(cr)
            i += 1
        co.set_organisation(creneaux_co,None)
    #Affectations cours-salles
    for co in cours:
        for sl in salles:
            if res.x[i] > 0.5:
                co.organisation.salle = sl
            i += 1



def build_compute_plne(cours, creneaux, salles, classes, profs, demi_journees=None, penalite_cours_creneau_seul=1, penalite_journee_travaillee=10, verbose=True):
    t1 = time()
    minimize,bounds,integrality,A,UB,LB,nb_var_cours_creneau,nb_var_cours_salle,nb_var_commence,nb_var_salle_affec,nb_var_cours_demijournee,nb_var_cours_journee,journees = generate_milp(cours, creneaux, salles, classes, profs, demi_journees=demi_journees, penalite_cours_creneau_seul=penalite_cours_creneau_seul, penalite_journee_travaillee=penalite_journee_travaillee, verbose=verbose)
    t2 = time()
    if verbose:
        print(str(int(t2-t1)),"secondes écoulées pour la génération des contraintes")
    res = compute_plne(minimize,bounds,integrality,A,UB,LB,verbose=verbose)

    t3 = time()
    if verbose:
        print(str(int(t3-t2)),"secondes écoulées pour la résolution du problème")
        print(str(int(t3-t1)),"secondes écoulées au total")
    
    refresh_objects_with_result(res,cours,creneaux,salles)
    return res


def compute_plne(minimize,bounds,integrality,A,UB,LB, verbose=True):
    
    if verbose:
        print("Nb contraintes : ",A.shape[0])
        print("Nb variables : ",A.shape[1])

    constraints = LinearConstraint(A,ub=UB,lb=LB)
    res = milp(c=minimize, bounds=bounds, constraints=constraints, integrality=integrality)

    if verbose:
        if not res.status in [0,1,4]:
            print("Impossible de trouver un résultat avec ces contraintes")
        else:
            print("Solution trouvée avec un score de",res.fun)

    return res