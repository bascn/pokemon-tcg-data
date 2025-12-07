#!/usr/bin/env python3
"""
Script para re-descargar TODA la data desde TCGdex
manteniendo el formato EXACTO de PokemonTCG API
"""

import json
import requests
from datetime import datetime
from typing import Dict, List, Any
import time

TCGDEX_API = "https://api.tcgdex.net/v2/en"
DATA_DIR = "/Users/bastiancaba/Desktop/Dev Projects/rpgstore api/pokemon-tcg-data"

def save_json_file(filename: str, data: Any):
    """Guarda un archivo JSON"""
    filepath = f"{DATA_DIR}/{filename}"
    print(f"Guardando {filename}...")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_all_sets_from_tcgdex() -> List[Dict]:
    """Obtiene todos los sets desde TCGdex"""
    print("Obteniendo lista de sets desde TCGdex...")
    try:
        response = requests.get(f"{TCGDEX_API}/sets", timeout=10)
        response.raise_for_status()
        sets = response.json()
        print(f"✓ {len(sets)} sets disponibles")
        return sets
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

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
    """
    # Construir el set info en formato PokemonTCG
    set_info = {
        "id": tcgdex_set.get('id'),
        "name": tcgdex_set.get('name'),
        "series": tcgdex_set.get('serie', {}).get('name', 'Unknown') if isinstance(tcgdex_set.get('serie'), dict) else 'Unknown',
        "printedTotal": tcgdex_set.get('cardCount', {}).get('official', 0),
        "total": tcgdex_set.get('cardCount', {}).get('total', 0),
        "releaseDate": tcgdex_set.get('releaseDate', ''),
    }
    
    # Agregar imágenes del set si existen
    if tcgdex_set.get('logo') or tcgdex_set.get('symbol'):
        set_info['images'] = {}
        if tcgdex_set.get('symbol'):
            set_info['images']['symbol'] = tcgdex_set.get('symbol')
        if tcgdex_set.get('logo'):
            set_info['images']['logo'] = tcgdex_set.get('logo')
    
    # Construir la carta en formato PokemonTCG
    card_id = f"{tcgdex_set.get('id')}-{tcgdex_card.get('localId', tcgdex_card.get('id', ''))}"
    
    converted = {
        "id": card_id,
        "name": tcgdex_card.get('name', ''),
        "supertype": tcgdex_card.get('category', 'Pokémon'),
    }
    
    # Subtypes
    if tcgdex_card.get('stage'):
        converted['subtypes'] = [tcgdex_card['stage']]
    elif tcgdex_card.get('suffix'):
        converted['subtypes'] = [tcgdex_card['suffix']]
    
    # HP
    if tcgdex_card.get('hp'):
        converted['hp'] = str(tcgdex_card['hp'])
    
    # Types
    if tcgdex_card.get('types'):
        converted['types'] = tcgdex_card['types']
    
    # Evolves From
    if tcgdex_card.get('evolveFrom'):
        converted['evolvesFrom'] = tcgdex_card['evolveFrom']
    
    # Abilities
    if tcgdex_card.get('abilities'):
        converted['abilities'] = []
        for ability in tcgdex_card['abilities']:
            converted['abilities'].append({
                'name': ability.get('name', ''),
                'text': ability.get('effect', ''),
                'type': ability.get('type', 'Ability')
            })
    
    # Attacks
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
    
    # Weaknesses
    if tcgdex_card.get('weaknesses'):
        converted['weaknesses'] = []
        for weakness in tcgdex_card['weaknesses']:
            converted['weaknesses'].append({
                'type': weakness.get('type', ''),
                'value': weakness.get('value', '×2')
            })
    
    # Resistances
    if tcgdex_card.get('resistances'):
        converted['resistances'] = []
        for resistance in tcgdex_card['resistances']:
            converted['resistances'].append({
                'type': resistance.get('type', ''),
                'value': resistance.get('value', '-30')
            })
    else:
        converted['resistances'] = []
    
    # Retreat Cost
    if tcgdex_card.get('retreatCost'):
        converted['retreatCost'] = tcgdex_card['retreatCost']
        converted['convertedRetreatCost'] = len(tcgdex_card['retreatCost'])
    
    # Set info
    converted['set'] = set_info
    
    # Number
    converted['number'] = str(tcgdex_card.get('localId', ''))
    
    # Artist
    if tcgdex_card.get('illustrator'):
        converted['artist'] = tcgdex_card['illustrator']
    
    # Rarity
    if tcgdex_card.get('rarity'):
        converted['rarity'] = tcgdex_card['rarity']
    
    # Flavor Text
    if tcgdex_card.get('description'):
        converted['flavorText'] = tcgdex_card['description']
    
    # Pokedex Numbers
    if tcgdex_card.get('dexId'):
        converted['nationalPokedexNumbers'] = tcgdex_card['dexId'] if isinstance(tcgdex_card['dexId'], list) else [tcgdex_card['dexId']]
    
    # Legalities
    if tcgdex_card.get('legal', {}).get('standard'):
        converted['legalities'] = {'standard': 'Legal'}
    else:
        converted['legalities'] = {'unlimited': 'Legal'}
    
    # Images - FORMATO CORRECTO DE TCGdex
    if tcgdex_card.get('image'):
        base_url = tcgdex_card['image']
        converted['images'] = {
            'small': f"{base_url}/low.jpg",
            'large': f"{base_url}/high.jpg"
        }
    
    # Regulationmark
    if tcgdex_card.get('regulationMark'):
        converted['regulationMark'] = tcgdex_card['regulationMark']
    
    return converted

def main():
    print("=" * 80)
    print("RE-DESCARGA COMPLETA DESDE TCGdex")
    print("Manteniendo formato PokemonTCG API")
    print("=" * 80)
    
    # 1. Obtener todos los sets
    all_sets = get_all_sets_from_tcgdex()
    if not all_sets:
        print("❌ No se pudieron obtener los sets")
        return
    
    print(f"\n📥 Se descargarán {len(all_sets)} sets completos")
    print("Esto tomará varios minutos...\n")
    
    # Estructuras para almacenar los datos
    all_cards = []
    index_by_set = {}
    index_by_type = {}
    index_by_name = {}
    
    # 2. Descargar cada set
    total_cards = 0
    for i, tcgdex_set_summary in enumerate(all_sets, 1):
        set_id = tcgdex_set_summary.get('id')
        set_name = tcgdex_set_summary.get('name')
        
        print(f"[{i}/{len(all_sets)}] {set_name} ({set_id})")
        
        # Obtener detalles completos del set
        set_details = get_set_details(set_id)
        if not set_details or 'cards' not in set_details:
            print(f"  ⚠️ Sin cartas")
            continue
        
        cards = set_details.get('cards', [])
        print(f"  📥 {len(cards)} cartas")
        
        # Convertir cada carta
        set_cards = []
        for tcgdex_card in cards:
            converted_card = convert_tcgdex_card_to_pokemontcg_format(tcgdex_card, set_details)
            
            # Agregar a todas las estructuras
            all_cards.append(converted_card)
            set_cards.append(converted_card)
            
            # Index by type
            types = converted_card.get('types', [converted_card.get('supertype', 'Unknown')])
            for card_type in types:
                if card_type not in index_by_type:
                    index_by_type[card_type] = []
                index_by_type[card_type].append(converted_card)
            
            # Index by name
            name = converted_card.get('name', 'Unknown')
            if name not in index_by_name:
                index_by_name[name] = []
            index_by_name[name].append(converted_card)
        
        # Index by set
        index_by_set[set_id] = set_cards
        total_cards += len(cards)
        
        print(f"  ✓ {len(cards)} cartas convertidas")
        
        # Pequeña pausa para no sobrecargar la API
        if i % 10 == 0:
            print(f"\n  💤 Pausa breve... ({i}/{len(all_sets)} sets completados)\n")
            time.sleep(2)
        else:
            time.sleep(0.2)
    
    # 3. Crear metadata
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
    
    # 4. Guardar archivos
    print("\n" + "=" * 80)
    print("Guardando archivos...")
    print("=" * 80)
    
    save_json_file('all-cards.json', all_cards)
    save_json_file('index-by-set.json', index_by_set)
    save_json_file('index-by-type.json', index_by_type)
    save_json_file('index-by-name.json', index_by_name)
    save_json_file('cards-metadata.json', metadata)
    
    # 5. Resumen
    print("\n" + "=" * 80)
    print("✅ DESCARGA COMPLETADA")
    print("=" * 80)
    print(f"Total de sets: {len(index_by_set)}")
    print(f"Total de cartas: {len(all_cards):,}")
    print(f"Cartas únicas por nombre: {len(index_by_name):,}")
    print(f"Tipos de carta: {len(index_by_type)}")
    print(f"\nFuente: TCGdex API")
    print(f"Formato: PokemonTCG API (compatible)")
    print(f"Última actualización: {metadata['lastUpdated']}")
    print(f"\n🖼️  Imágenes:")
    print(f"  • Todas desde TCGdex")
    print(f"  • Sin reverso de carta")
    print(f"  • Alta calidad disponible")
    print("=" * 80)

if __name__ == "__main__":
    main()
