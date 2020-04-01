
# Unit tests

## Fonctionnement en bref
- La classe `BlenderTestCase` lance deux Blender (un sender et un receiver) qui exécutent `python_server.py`.
- `python_server.py` enregistre un opérateur qui gère une boucle asyncio. 
- La boucle exécute un serveur qui reçoit du source python, le compile et l'exécute. Blender n'est pa bloqué entre deux exécutions et on voit le déroulement du test
- le test (voir `test_test.py`) envoie du code source au Blender 'sender'. D'abord une commande de connection et join room, puis les fonctions du test à proprement parler.
- pour l'instant la conclusion est décidée manuellement
  - pour un succès, quitter un Blender
  - pour un échec, utilisezr le panneau 3D nommé TEST et cliquer sur Fail

Limites : je n'ai pas géré la comparaison automatique de fichiers. Ca ne marche pas tout seul parce que les fichiers qui ne sont pas identiques en binaire.

Evolution possible : on devrait pouvoir utiliser plusieurs sender et receiver pour faire des tests de charge

## Activer les tests

Command palette : **Python: Configure Tests**, choisir **unittest**, pattern : **test_***

Definir la variables d'environnement DCCSYNC_BLENDER_EXE_PATH

Détails dans https://code.visualstudio.com/docs/python/testing#_enable-a-test-framework

## Ecrire un test
Voir `tests\test_test.py`

## Debugger les tests
Coté Blender, `python_server.py` autorise la connexion du debugger sur les ports spécifiés dans `BlenderTestCase`. Pour attacher le debugger, il faut ajouter deux  configuration de debug, une avec 5688 (sender) et une avec 5689 (receiver):
>
    {
        "name": "Attach to sender (5688)",
        "type": "python",
        "request": "attach",
        "port": 5688,
        "host": "localhost",
        "pathMappings": [
            {
                "localRoot": "${workspaceFolder}",
                "remoteRoot": "."
            }
        ]
    },
        {
        "name": "Attach to senreceiver (5689)",
        "type": "python",
        "request": "attach",
        "port": 5689,
        "host": "localhost",
        "pathMappings": [
            {
                "localRoot": "${workspaceFolder}",
                "remoteRoot": "."
            }
        ]
    },

>

Ensuite:

- mettre un breakpoint dans le code de dccsync avec une des deux méthodes suivantes : 
  - ajouter un appel au builtin `breakpoint()` dans le code. Attention le breakpoint ouvrira le fichier qui est dans %ADDPATA% (vois ci dessous) et ne sera pas editable dans VSCode
  - Ouvrir le fichier de code situé dans `%APPDATA%Blender Foundation\Blender\2.82\scripts\addons\dccsync` et y mettre un breakpoint avec VSCode
- démarrer l'exécution du test unitaire : Blender se bloque en attendant l'attachement
- attacher le debugger : l'exécution continue jusqu'au breakpoint

## Caveat
```bpy.context.window``` is ```None``` and may cause crashes. For ```instance bpy.data.scenes.remove(my_scene)``` because ```CTX_wm_window()``` returns ```NULL```, but ```bpy.ops.scene.delete({'scene': my_scene})``` succeeds. In fact ```bpy.context.window``` is ```None``` in a script run from ```--python``` argument.

A possible solution could be to run the asyncio operator in python_server from a load handler.

# Misc
## Guidelines
- Use name_full instead of name for Blender objects (because of external links)

## Blender stuff

import bmesh
bm = bmesh.new() bm.free()

obj = bpy.context.selected_objects[0]

bm.from_mesh(obj.data)

bm.verts.ensure_lookup_table()

triangles = bm.calc_loop_triangles()

comparaison de matrices marche pas

l'undo est un hack => graph non updaté sur undo

bmesh supporte pas les custom normals

grease pencil n'est pas un mesh standard

bpy.msgbus.subscribe_rna est appelé dans le viewport pas dans l'inspecteur

replace data of an object pas possible

instance de material par parametre

problème de nommage 2 objets ne peuvent pas avoir le même nom, meme dans des hierarchies différentes
pire, parfois on renomme un objet, l'ui ne refuse pas mais renomme un autre objet, peut-être d'une autre scene

_UL_
property index pour une liste UI

obj.select = True -> étrange, un seul set de seléction ?

intialization des custom properties dans un timer !

pas de callback app start/end => test de l'existence d'une window...

bpy.context.active_object.mode != 'OBJECT' le mode objet est stocké sur l'objet actif !

bpy.ops.object.delete() marche pas

link changement de transform possible en script mais pas en UI

les lights ont des parametres différents en fonciton du render engine:
exemple : light.cycles.cast_shadow vs light.use_shadow

mat.node_tree.links.new(bsdf.inputs['Base Color'], texImage.outputs['Color']) je l'aurais fait dans l'autre sens...

set parametre sur une multi selection marche à moitié

Si il manque des textures, le .blend ne se charge pas (à vérifier)
 
un fichier ne peut pas s'appeler null.blend (quelles sont les autres contraintes ?)

normal map Red & Green inverted, quel est le standard ?

pas (toujours) de messages de visibilité des objets / collections 

visible_get() vs hide_viewport

bpy.app.handlers.depsgraph_update_pre Débile

les handlers ne sont pas appelés pour les suppression et renommage de collections

update.id.original dans les updates, le .original est le nouveau !

pas d'update (handler) sur les scenes dépendentes

crash quand on lit des infos d'update liés à des collections ajoutées/détruites

hide_viewport sur collection -> reception du message quand hide_viewport=True pas quand hide_viewport=False

collection invisible, pre handler l'update remove from collection n'est pas notifié, 
changement de collection d'un object -> pas de notif du tout d'une collection invisible à une collection invisible

material.grease_pencil !!!

stroke.points.add(count) vs stroke.points.pop()

quand on supprime un grease pencil, il en reste une trace dans bpy.data.grease_pencils -> orphan data

recherche dans bpy.data.objects par name, pas par name_full