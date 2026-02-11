#!/usr/bin/env python3
"""
Script para descargar SOLO los sets faltantes desde TCGdex
y agregarlos a los archivos JSON existentes.
"""

import json
import requests
from datetime import datetime
from typing import Dict, List, Any
import time

TCGDEX_API = "https://api.tcgdex.net/v2/en"
DATA_DIR = "/Users/bastiancaba/Desktop/Dev Projects/rpgstore api/pokemon-tcg-data"

# Sets faltantes identificados
MISSING_SET_IDS = ["B1a", "B2", "me02.5"]


def load_json_file(filename: str) -> Any:
    """Carga un archivo JSON existente"""
    filepath = f"{DATA_DIR}/{filename}"
    print(f"Cargando {filename}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json_file(filename: str, data: Any):
    """Guarda un archivo JSON"""
    filepath = f"{DATA_DIR}/{filename}"
    print(f"Guardando {filename}...")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_set_details(set_id: str) -> Dict:
    """Obtiene los detalles completos de un set con sus cartas"""
    try:
        response = requests.get(f"{TCGDEX_API}/sets/{set_id}", timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"  ❌ Error obteniendo {set_id}: {e}")
        return None


def convert_tcgdex_card_to_pokemontcg_format(tcgdex_card: Dict, tcgdex_set: Dict) -> Dict:
    """
    Convierte una carta de TCGdex al formato EXACTO de PokemonTCG API
    (Misma función que en rebuild-from-tcgdex.py)
    """
    set_info = {
        "id": tcgdex_set.get('id'),
        "name": tcgdex_set.get('name'),
        "series": tcgdex_set.get('serie', {}).get('name', 'Unknown') if isinstance(tcgdex_set.get('serie'), dict) else 'Unknown',
        "printedTotal": tcgdex_set.get('cardCount', {}).get('official', 0),
        "total": tcgdex_set.get('cardCount', {}).get('total', 0),
        "releaseDate": tcgdex_set.get('releaseDate', ''),
    }

    if tcgdex_set.get('logo') or tcgdex_set.get('symbol'):
        set_info['images'] = {}
        if tcgdex_set.get('symbol'):
            set_info['images']['symbol'] = tcgdex_set.get('symbol')
        if tcgdex_set.get('logo'):
            set_info['images']['logo'] = tcgdex_set.get('logo')

    card_id = f"{tcgdex_set.get('id')}-{tcgdex_card.get('localId', tcgdex_card.get('id', ''))}"

    converted = {
        "id": card_id,
        "name": tcgdex_card.get('name', ''),
        "supertype": tcgdex_card.get('category', 'Pokémon'),
    }

    if tcgdex_card.get('stage'):
        converted['subtypes'] = [tcgdex_card['stage']]
    elif tcgdex_card.get('suffix'):
        converted['subtypes'] = [tcgdex_card['suffix']]

    if tcgdex_card.get('hp'):
        converted['hp'] = str(tcgdex_card['hp'])

    if tcgdex_card.get('types'):
        converted['types'] = tcgdex_card['types']

    if tcgdex_card.get('evolveFrom'):
        converted['evolvesFrom'] = tcgdex_card['evolveFrom']

    if tcgdex_card.get('abilities'):
        converted['abilities'] = []
        for ability in tcgdex_card['abilities']:
            converted['abilities'].append({
                'name': ability.get('name', ''),
                'text': ability.get('effect', ''),
                'type': ability.get('type', 'Ability')
            })

    if tcgdex_card.get('attacks'):
        converted['attacks'] = []
        for attack in tcgdex_card['attacks']:
            attack_data = {
                'name': attack.get('name', ''),
                'cost': attack.get('cost', []),
                'convertedEnergyCost': len(attack.get('cost', [])),
            }
            if attack.get('damage'):
                attack_data['damage'] = str(attack['damage'])
            if attack.get('effect'):
                attack_data['text'] = attack['effect']
            converted['attacks'].append(attack_data)

    if tcgdex_card.get('weaknesses'):
        converted['weaknesses'] = []
        for weakness in tcgdex_card['weaknesses']:
            converted['weaknesses'].append({
                'type': weakness.get('type', ''),
                'value': weakness.get('value', '×2')
            })

    if tcgdex_card.get('resistances'):
        converted['resistances'] = []
        for resistance in tcgdex_card['resistances']:
            converted['resistances'].append({
                'type': resistance.get('type', ''),
                'value': resistance.get('value', '-30')
            })
    else:
        converted['resistances'] = []

    if tcgdex_card.get('retreatCost'):
        converted['retreatCost'] = tcgdex_card['retreatCost']
        converted['convertedRetreatCost'] = len(tcgdex_card['retreatCost'])

    converted['set'] = set_info
    converted['number'] = str(tcgdex_card.get('localId', ''))

    if tcgdex_card.get('illustrator'):
        converted['artist'] = tcgdex_card['illustrator']

    if tcgdex_card.get('rarity'):
        converted['rarity'] = tcgdex_card['rarity']

    if tcgdex_card.get('description'):
        converted['flavorText'] = tcgdex_card['description']

    if tcgdex_card.get('dexId'):
        converted['nationalPokedexNumbers'] = tcgdex_card['dexId'] if isinstance(tcgdex_card['dexId'], list) else [tcgdex_card['dexId']]

    if tcgdex_card.get('legal', {}).get('standard'):
        converted['legalities'] = {'standard': 'Legal'}
    else:
        converted['legalities'] = {'unlimited': 'Legal'}

    if tcgdex_card.get('image'):
        base_url = tcgdex_card['image']
        converted['images'] = {
            'small': f"{base_url}/low.jpg",
            'large': f"{base_url}/high.jpg"
        }

    if tcgdex_card.get('regulationMark'):
        converted['regulationMark'] = tcgdex_card['regulationMark']

    return converted


def main():
    print("=" * 80)
    print("DESCARGA DE SETS FALTANTES DESDE TCGdex")
    print(f"Sets a descargar: {', '.join(MISSING_SET_IDS)}")
    print("=" * 80)

    # 1. Cargar archivos existentes
    print("\n📂 Cargando datos existentes...")
    all_cards = load_json_file('all-cards.json')
    index_by_set = load_json_file('index-by-set.json')
    index_by_type = load_json_file('index-by-type.json')
    index_by_name = load_json_file('index-by-name.json')

    print(f"  Cartas existentes: {len(all_cards):,}")
    print(f"  Sets existentes: {len(index_by_set)}")

    # 2. Descargar cada set faltante
    total_new_cards = 0
    for i, set_id in enumerate(MISSING_SET_IDS, 1):
        print(f"\n[{i}/{len(MISSING_SET_IDS)}] Descargando set: {set_id}")

        set_details = get_set_details(set_id)
        if not set_details or 'cards' not in set_details:
            print(f"  ⚠️ Sin cartas para {set_id}")
            continue

        set_name = set_details.get('name', 'Unknown')
        cards = set_details.get('cards', [])
        print(f"  📦 {set_name} - {len(cards)} cartas")

        set_cards = []
        for tcgdex_card in cards:
            converted_card = convert_tcgdex_card_to_pokemontcg_format(tcgdex_card, set_details)

            # Agregar a all-cards
            all_cards.append(converted_card)
            set_cards.append(converted_card)

            # Agregar a index-by-type
            types = converted_card.get('types', [converted_card.get('supertype', 'Unknown')])
            for card_type in types:
                if card_type not in index_by_type:
                    index_by_type[card_type] = []
                index_by_type[card_type].append(converted_card)

            # Agregar a index-by-name
            name = converted_card.get('name', 'Unknown')
            if name not in index_by_name:
                index_by_name[name] = []
            index_by_name[name].append(converted_card)

        # Agregar a index-by-set
        index_by_set[set_id] = set_cards
        total_new_cards += len(cards)

        print(f"  ✅ {len(cards)} cartas agregadas")

        # Pausa para no sobrecargar la API
        if i < len(MISSING_SET_IDS):
            time.sleep(1)

    # 3. Actualizar metadata
    metadata = {
        "totalCards": len(all_cards),
        "lastUpdated": datetime.now().isoformat() + 'Z',
        "version": "2.0",
        "source": "TCGdex",
        "indices": {
            "byName": len(index_by_name),
            "bySet": len(index_by_set),
            "byType": len(index_by_type)
        }
    }

    # 4. Guardar todos los archivos actualizados
    print("\n" + "=" * 80)
    print("💾 Guardando archivos actualizados...")
    print("=" * 80)

    save_json_file('all-cards.json', all_cards)
    save_json_file('index-by-set.json', index_by_set)
    save_json_file('index-by-type.json', index_by_type)
    save_json_file('index-by-name.json', index_by_name)
    save_json_file('cards-metadata.json', metadata)

    # 5. Resumen
    print("\n" + "=" * 80)
    print("✅ ACTUALIZACIÓN COMPLETADA")
    print("=" * 80)
    print(f"Sets nuevos agregados: {len(MISSING_SET_IDS)}")
    print(f"Cartas nuevas: {total_new_cards:,}")
    print(f"Total de sets ahora: {len(index_by_set)}")
    print(f"Total de cartas ahora: {len(all_cards):,}")
    print(f"Última actualización: {metadata['lastUpdated']}")
    print("=" * 80)


if __name__ == "__main__":
    main()
