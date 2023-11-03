
import numpy as np
from time import time
from mip import Model, MINIMIZE, CBC, INTEGER, OptimizationStatus, xsum
import itertools
def generate_milp(cours, creneaux, salles, classes, profs, demi_journees=None, verbose=False, penalite_cours_creneau_seul=1, penalite_journee_travaillee=10, contraintes_salles=True):
    if verbose:
        print("génération des variables")
    
    nb_var_cours_creneau = 0
    nb_var_cours_salle = 0
    nb_var_commence = 0
    nb_var_salle_affec = 0
    nb_var_cours_journee = 0
    nb_var_cours_seul = 0

    model = Model(sense=MINIMIZE, solver_name=CBC)

    cours_creneau = {}
    cours_salle = {}
    cours_commence_creneau = {}
    cours_salle_creneau = {}
    creneau_seul = {}
    cours_journee = {}

    #Rappel des variables
    #cours_créneau(co, cr) signifie que le cours co a lieu durant le créneau cr
    for co in cours:
        for cr in creneaux:
            cours_creneau[(co,cr)] = model.add_var(name="cours_creneau("+str(co.numero)+","+str(cr.numero)+")",var_type=INTEGER,lb=0,ub=1)
            nb_var_cours_creneau += 1
    #cours_salle(co, sl) signifie que le cours co a lieu dans la salle sl
    if contraintes_salles:
        for co in cours:
            for sl in salles:
                cours_salle[(co,sl)] = model.add_var(name="cours_salle("+str(co.numero)+","+str(sl.numero)+")",var_type=INTEGER,lb=0,ub=1)
                nb_var_cours_salle += 1
    #cours_commence_créneau(co, cr) signifie que le cours co a lieu durant le créneau cr
    for co in cours:
        for cr in creneaux:
            cours_commence_creneau[(co,cr)] = model.add_var(name="cours_commence_creneau("+str(co.numero)+","+str(cr.numero)+")",var_type=INTEGER,lb=0,ub=1)
            nb_var_commence += 1
    #cours_salle_creneau(co, sl, cr) = le cours est dans cette salle durant ce créneau
    if contraintes_salles:
        for sl in salles:
            for cr in creneaux:
                for co in cours:
                    cours_salle_creneau[(co,sl,cr)] = model.add_var(name="cours_salle_creneau("+str(co.numero)+","+str(sl.numero)+","+str(cr.numero)+")",var_type=INTEGER,lb=0,ub=1)
                    nb_var_salle_affec += 1

    nb_var = nb_var_cours_creneau+nb_var_cours_salle+nb_var_commence+nb_var_salle_affec

    #creneau_seul(co, cr) = si le cours commence au créneau cr il n'a pas de voisin
    if demi_journees != None:
        demi_journees = [(i,dj) for i,dj in enumerate(demi_journees)]
        
        
        if penalite_cours_creneau_seul != 0:
            for co in cours:
                for cr in creneaux:
                    creneau_seul[(co,cr)] = model.add_var(name="creneau_seul("+str(co.numero)+","+str(cr.numero)+")", var_type=INTEGER,lb=0,ub=1)
                    nb_var_cours_seul += 1
            nb_var += nb_var_cours_seul

        journees = []
        for dj in demi_journees:
            if dj[0]%2 == 0:
                journees.append([dj])
            else:
                journees[-1].append(dj)
            
    #cours_journee(pr, j) = le prof a cours durant la journee j
        for pr in profs:
            for j_idx,j in enumerate(journees):
                cours_journee[(pr,j_idx)] = model.add_var(name="cours_journee("+str(pr.numero)+","+str(dj[0])+")", var_type=INTEGER,lb=0,ub=1)
                nb_var_cours_journee += 1
        nb_var += nb_var_cours_journee


    # 0] Pour tout prof pr, journée j, nb_mini_de_cours(pr)*cours_journee(pr,j) - somme [cours co de pr, créneau cr dans j] cours_commence_creneau(co, cr) <= 0
    for pr in profs:
        nb_heure_cours_prof_total = 0
        for duree in [co.duree for co in cours if co.prof is pr]:
            nb_heure_cours_prof_total += duree
        for j_idx,j in enumerate(journees):
            model += min(pr.nb_heures_cours_mini_par_jour,nb_heure_cours_prof_total) * cours_journee[(pr,j_idx)] - xsum(cours_commence_creneau[(co, cr)]*co.duree for (co,cr) in itertools.product([co for co in cours if co.prof is pr],[cr for dj in j for cr in dj[1]])) <= 0

    # 1] Pour tout cours co : somme [salle sl tq cours_doit_salle(co, sl)] >= 1
    
    if contraintes_salles:
        if verbose:
            print("génération contrainte 1")

        for co in cours:
            if len(co.contraintes_salle) > 0:
                model += xsum(cours_salle[(co,sl)] for sl in co.contraintes_salle) >= 1
 
    # 2] Pour tout cours co, tout créneau cr : si cours_pas_creneau(co, cr) = 1 alors cours_créneau(co, cr) <= 0
    if verbose:
        print("génération contrainte 2")
    for co in cours:
        if co.prof != None and len(co.prof.contraintes_pas_cours) > 0:
            model += xsum(cours_creneau[(co,cr)] for cr in co.prof.contraintes_pas_cours) <= 0

    # 3] Pour tous les cours co : (somme [cr dans CRENEAUX] cours_créneau(co, cr)) = durée_cours(co)
    if verbose:
        print("génération contrainte 3")
    for co in cours:
        model += xsum(cours_creneau[(co,cr)] for cr in creneaux) == co.duree

    # 4] Pour toute salle sl, creneau cr, somme [co dans COURS] cours_salle_creneau(co,sl,cr) <= 1
    
    if contraintes_salles:
        if verbose:
            print("génération contrainte 4")
    
        for sl in salles:
            for cr in creneaux:
                model += xsum(cours_salle_creneau[(co,sl,cr)] for co in cours) <= 1

    # 5] Pour chaque cours co1,co2 qui ont le même prof, et tout créneau cr : cours_creneau(co1, cr) + cours_creneau(co2, cr) <= 1
    if verbose:
        print("génération contrainte 5")
    c_done = []
    for co1 in cours:
        c_done.append(co1)
        for co2 in cours:
            if (co1.prof != None) and (co2.prof != None) and (not co2 in c_done) and co1.prof is co2.prof:
                for cr in creneaux:
                    model += cours_creneau[(co1,cr)] + cours_creneau[(co2,cr)] <= 1
        

    # 6.a] pour tout cours co, créneau cr,
    # durée_cours(co) * cours_commence_créneau(co, cr) - (somme [créneaux cr2 qui suivent le créneau cr sur la durée du cours co] cours_creneau(co, cr2)) <= 0
    if verbose:
        print("génération contrainte 6a")
    for co in cours:
        for cr in creneaux:
            suivants = cr.get_suivants()[:co.duree]
            model += co.duree*cours_commence_creneau[(co,cr)] - xsum(cours_creneau[(co,cr2)] for cr2 in suivants) <= 0

    # 6.b] Pour tout cours co : somme[cr dans CRENAUX] cours_commence_créneau(co, cr) = 1
    if verbose:
        print("génération contrainte 6b")
    for co in cours:
        model += xsum(cours_commence_creneau[(co,cr)] for cr in creneaux) == 1

    # 7] Pour toute classe cl et tout créneau cr : somme [co les COURS concernant la classe cl] cours_créneau(co, cr) <= 1
    if verbose:
        print("génération contrainte 7")
    for cl in classes:
        for cr in creneaux:
            model += xsum(cours_creneau[(co,cr)] for co in cours if co.classe is cl) <= 1


    # 8] Pour tout cours co : (somme [sl les SALLES] cours_salle(co, sl)) = 1
    if contraintes_salles:
        if verbose:
            print("génération contrainte 8")
        for co in cours:
            model += xsum(cours_salle[(co,sl)] for sl in salles) == 1

    # 9] Pour chaque cours co1,co2 qui sont mutex, et tout créneau cr : cours_creneau(co1, cr) + cours_creneau(co2, cr) <= 1
    if verbose:
        print("génération contrainte 9")
    for co1 in cours:
        for co2 in cours:
            if co2.classe in co1.classe.mutex:
                for cr in creneaux:
                    model += cours_creneau[(co1,cr)] + cours_creneau[(co2,cr)] <= 1

    # 10] Pour chaque cours co qui est contraint par des créneaux, pour tout créneau cr, si cr n'est pas dans les contraintes alors cours_creneau(co, cr) <= 0
    if verbose:
        print("génération contrainte 10")
    for co in cours:
        if len(co.contrainte_dans_creneaux) > 0:
            model += xsum(cours_creneau[(co,cr)] for cr in creneaux if not cr in co.contrainte_dans_creneaux) <= 0

    # 11] Pour tout cours co, toute salle sl : cours_salle(co, sl)*taille(classe(co)) <= taille(sl)
        
    if contraintes_salles:
        if verbose:
            print("génération contrainte 11")
    
        for co in cours:
            for sl in salles:
                if (not np.isinf(sl.effectifs)) and co.classe.effectifs > 0:
                    model += co.classe.effectifs * cours_salle[(co,sl)] <= sl.effectifs

    # 12] cours_salle_creneau(co, sl, cr) doit être 1 si jamais il y a le cours co dans le créneau cr dans la salle sl
    # pour tout cours co, salle sl, créneau cr, cours_creneau(co, cr) + cours_salle(co, sl) - cours_salle_creneau(co, sl, cr) <= 1 (cours_creneau(co, cr) et cours_salle(co, sl) => cours_salle_creneau(co, sl, cr))
    if contraintes_salles:
        if verbose:
            print("génération contrainte 12")
    
        for co in cours:
            for cr in creneaux:
                for sl in salles:
                    model += cours_creneau[(co,cr)] + cours_salle[(co,sl)] - cours_salle_creneau[(co,sl,cr)] <= 1

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
                                model += cours_creneau[(co,cr)] - cours_journee[(pr,i)] <= 0


    # 13b] Pour tous les profs pr, pour tous les cours co de pr, pour tous les créneaux, (somme[co1 dans COURS de p] cours_creneau(co1,cr-1)) + (somme[co1 dans COURS de p] cours_creneau(co1,cr+duree(co))) + cours_seul(co,cr) >= 1

    if penalite_cours_creneau_seul != 0 and demi_journees != None:
        if verbose:
            print("génération contrainte 13b.v2")
        for pr in profs:
            for co in cours:
                if co.prof is pr:
                    for j in journees:
                        first_creneau_numero = j[0][1][0].numero
                        last_creneau_numero = j[-1][1][-1].numero
                        for dj_index,dj in j:
                            for cr in dj:
                                if cr.numero != first_creneau_numero:
                                    sum_before = xsum(cours_creneau[(co1,creneaux[cr.numero-1])] for co1 in cours if co1.prof is pr)
                                if cr.numero + co.duree - 1 < last_creneau_numero:
                                    sum_after = xsum(cours_creneau[(co1,creneaux[cr.numero+co.duree])] for co1 in cours if co1.prof is pr)
                                if cr.numero == first_creneau_numero:
                                    model += sum_after + creneau_seul[(co,cr)] - cours_commence_creneau[(co,cr)] >= 0
                                elif cr.numero + co.duree + 1 >= last_creneau_numero:
                                    model += sum_before + creneau_seul[(co,cr)] - cours_commence_creneau[(co,cr)] >= 0
                                else:
                                    model += sum_after + sum_before + creneau_seul[(co,cr)] - cours_commence_creneau[(co,cr)] >= 0
                        

    #Objectif

    # A] certains cours donnent une pénalité de k point si ils ont lieu durant un créneau
    # pour chaque cours : pénalité(co,cr) = (somme [cr dans creneaux] cours_creneau(co,cr)) * pénalité (2 ici)
    if verbose:
        print("génération des préférences")
    
    objective_coef = []
    #pénalité préférences pas cours prof
    for co in cours:
        if co.prof != None:
            for cr in co.prof.contraintes_pref_pas_cours:
                objective_coef.append((co.prof.contraintes_pref_pas_cours[cr],cours_creneau[(co,cr)]))

    #B] pénalité cours dans mauvaise salle
    if contraintes_salles:
        for co in cours:
            for sl in salles:
                objective_coef.append((sl.penalite_salle,cours_salle[(co,sl)]))

    #C] bonus si prof a cours dans une salle qu'il aime
    #pénalité
    if contraintes_salles:
        for co in cours:
            if co.prof != None:
                for sl in co.prof.bonus_salle:
                    objective_coef.append((-co.prof.bonus_salle[sl],cours_salle[(co,sl)]))

    #D] 1] pénalités pour les créneaux seuls 2] pénalité du nombre de journées travaillées par les profs
    if demi_journees != None:
        if penalite_cours_creneau_seul != 0:
            for v in creneau_seul.values():
                objective_coef.append((penalite_cours_creneau_seul,v))
        for v in cours_journee.values():
            objective_coef.append((penalite_journee_travaillee,v))

    model.objective = xsum(coef * var for coef,var in objective_coef)

    return model,cours_creneau,cours_salle,cours_commence_creneau,cours_salle_creneau,creneau_seul,cours_journee,journees


def refresh_objects_with_result(model, cours, creneaux, salles, cours_creneau, cours_salle, cours_commence_creneau, cours_salle_creneau, creneau_seul, cours_journee):
    
    best_k = -1
    best_k_val = np.inf
    for k in range(model.num_solutions):
        if model.objective_values[k] < best_k_val:
            best_k = k
            best_k_val = model.objective_values[k]
    
    i = 0
    #Affectations cours-creneaux
    for co in cours:
        creneaux_co = []
        for cr in creneaux:
            if cours_creneau[(co,cr)].xi(best_k) >= 0.5:
                creneaux_co.append(cr)
            i += 1
        co.set_organisation(creneaux_co,None)
    #Affectations cours-salles
    for co in cours:
        for sl in salles:
            if (co,sl) in cours_salle and cours_salle[(co,sl)].xi(best_k) > 0.5:
                co.organisation.salle = sl
            i += 1




def build_compute_plne(cours, creneaux, salles, classes, profs, demi_journees=None, penalite_cours_creneau_seul=1, penalite_journee_travaillee=10, verbose=True, max_time=None, contraintes_salles=True, mip_preprocess=False):
    t1 = time()
    model,cours_creneau,cours_salle,cours_commence_creneau,cours_salle_creneau,creneau_seul,cours_journee,journees = generate_milp(cours, creneaux, salles, classes, profs, demi_journees=demi_journees, penalite_cours_creneau_seul=penalite_cours_creneau_seul, penalite_journee_travaillee=penalite_journee_travaillee, verbose=verbose, contraintes_salles=contraintes_salles)
    t2 = time()
    if verbose:
        print(str(int(t2-t1)),"secondes écoulées pour la génération des contraintes")
    status = compute_plne(model,verbose=verbose,max_time=max_time,mip_preprocess=mip_preprocess)
    print("Status :",status)
    t3 = time()
    if verbose:
        print(str(int(t3-t2)),"secondes écoulées pour la résolution du problème")
        print(str(int(t3-t1)),"secondes écoulées au total")
    
    refresh_objects_with_result(model,cours,creneaux,salles,cours_creneau,cours_salle,cours_commence_creneau,cours_salle_creneau,creneau_seul,cours_journee)
    return model


def compute_plne(model, max_time=None, verbose=True, mip_preprocess=True):
    
    model.emphasis = 3
    if not mip_preprocess:
        model.preprocess = 0
    
    if max_time == None:
        status = model.optimize()
    else:
        status = model.optimize(max_seconds_same_incumbent=max_time)
        

    if verbose:
        if status in [OptimizationStatus.ERROR,OptimizationStatus.INFEASIBLE,OptimizationStatus.INT_INFEASIBLE,OptimizationStatus.NO_SOLUTION_FOUND]:
            print("Impossible de trouver un résultat avec ces contraintes")
        else:
            print("Solution trouvée avec le résultat",status)

    return status