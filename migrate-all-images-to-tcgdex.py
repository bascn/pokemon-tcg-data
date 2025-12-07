#!/usr/bin/env python3
"""
Script para migrar TODAS las imágenes de pokemontcg.io a TCGdex
"""

import json
import requests
from datetime import datetime
import time

DATA_DIR = "/Users/bastiancaba/Desktop/Dev Projects/rpgstore api/pokemon-tcg-data"
TCGDEX_API = "https://api.tcgdex.net/v2/en"

def load_json_file(filename: str):
    """Carga un archivo JSON"""
    filepath = f"{DATA_DIR}/{filename}"
    print(f"Cargando {filename}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json_file(filename: str, data):
    """Guarda un archivo JSON"""
    filepath = f"{DATA_DIR}/{filename}"
    print(f"Guardando {filename}...")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_tcgdex_set_mapping():
    """
    Obtiene un mapeo de IDs de PokemonTCG a TCGdex
    Algunos sets tienen IDs diferentes entre las dos APIs
    """
    print("\nObteniendo sets de TCGdex...")
    try:
        response = requests.get(f"{TCGDEX_API}/sets", timeout=10)
        response.raise_for_status()
        tcgdex_sets = response.json()
        
        # Crear mapeo
        mapping = {}
        for tset in tcgdex_sets:
            tcgdex_id = tset.get('id')
            # TCGdex usa el mismo ID que PokemonTCG para la mayoría
            mapping[tcgdex_id] = tcgdex_id
        
        print(f"✓ {len(mapping)} sets disponibles en TCGdex")
        return mapping, tcgdex_sets
    except Exception as e:
        print(f"❌ Error: {e}")
        return {}, []

def get_card_from_tcgdex(set_id: str, card_number: str):
    """Intenta obtener una carta específica de TCGdex"""
    try:
        # TCGdex usa el número de carta como ID local
        url = f"{TCGDEX_API}/sets/{set_id}/{card_number}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def convert_to_tcgdex_image_url(set_id: str, card_number: str):
    """Construye la URL de imagen de TCGdex basándose en set_id y número"""
    # Formato: https://assets.tcgdex.net/en/{serie}/{set_id}/{card_number}/high.jpg
    
    # Necesitamos determinar la serie basándonos en el set_id
    serie_map = {
        'base': ['base1', 'base2', 'base3', 'base4', 'base5', 'basep'],
        'gym': ['gym1', 'gym2'],
        'neo': ['neo1', 'neo2', 'neo3', 'neo4'],
        'legendary': ['base6'],
        'ecard': ['ecard1', 'ecard2', 'ecard3'],
        'ex': ['ex1', 'ex2', 'ex3', 'ex4', 'ex5', 'ex6', 'ex7', 'ex8', 'ex9', 'ex10', 'ex11', 'ex12', 'ex13', 'ex14', 'ex15', 'ex16'],
        'dp': ['dp1', 'dp2', 'dp3', 'dp4', 'dp5', 'dp6', 'dp7'],
        'pl': ['pl1', 'pl2', 'pl3', 'pl4'],
        'hgss': ['hgss1', 'hgss2', 'hgss3', 'hgss4'],
        'bw': ['bw1', 'bw2', 'bw3', 'bw4', 'bw5', 'bw6', 'bw7', 'bw8', 'bw9', 'bw10', 'bw11'],
        'xy': ['xy0', 'xy1', 'xy2', 'xy3', 'xy4', 'xy5', 'xy6', 'xy7', 'xy8', 'xy9', 'xy10', 'xy11', 'xy12'],
        'sm': ['sm1', 'sm2', 'sm3', 'sm4', 'sm5', 'sm6', 'sm7', 'sm8', 'sm9', 'sm10', 'sm11', 'sm12'],
        'swsh': ['swsh1', 'swsh2', 'swsh3', 'swsh4', 'swsh5', 'swsh6', 'swsh7', 'swsh8', 'swsh9', 'swsh10', 'swsh11', 'swsh12'],
        'sv': ['sv1', 'sv2', 'sv3', 'sv4', 'sv5', 'sv6', 'sv7', 'sv8', 'sv9', 'sv10'],
        'me': ['me01', 'me02'],
        'tcgp': ['B1'],
    }
    
    # Determinar la serie
    serie = None
    for s, sets in serie_map.items():
        if set_id in sets or set_id.startswith(tuple(sets)):
            serie = s
            break
    
    if not serie:
        # Intentar inferir de los prefijos
        if set_id.startswith('sv'):
            serie = 'sv'
        elif set_id.startswith('swsh'):
            serie = 'swsh'
        elif set_id.startswith('sm'):
            serie = 'sm'
        elif set_id.startswith('xy'):
            serie = 'xy'
        elif set_id.startswith('bw'):
            serie = 'bw'
        elif set_id.startswith('dp'):
            serie = 'dp'
        elif set_id.startswith('ex'):
            serie = 'ex'
        else:
            serie = 'base'  # fallback
    
    # Formatear el número (debe ser string de 3 dígitos generalmente)
    formatted_number = str(card_number).zfill(3) if card_number.isdigit() else card_number
    
    base_url = f"https://assets.tcgdex.net/en/{serie}/{set_id}/{formatted_number}"
    
    return {
        'small': f"{base_url}/low.jpg",
        'large': f"{base_url}/high.jpg"
    }

def update_card_images(cards: list, set_mapping: dict) -> int:
    """Actualiza las imágenes de una lista de cartas"""
    updated_count = 0
    
    for card in cards:
        # Obtener información del set
        card_set = card.get('set', {})
        set_id = card_set.get('id') if isinstance(card_set, dict) else None
        card_number = card.get('number', '')
        
        if not set_id or not card_number:
            continue
        
        # Verificar si ya tiene imágenes de TCGdex
        current_images = card.get('images', {})
        if current_images.get('small', '').startswith('https://assets.tcgdex.net'):
            continue  # Ya está usando TCGdex
        
        # Generar nueva URL de TCGdex
        new_images = convert_to_tcgdex_image_url(set_id, card_number)
        
        card['images'] = new_images
        updated_count += 1
    
    return updated_count

def main():
    print("=" * 80)
    print("MIGRACIÓN COMPLETA DE IMÁGENES A TCGdex")
    print("=" * 80)
    print("\nEsto actualizará TODAS las cartas para usar imágenes de TCGdex")
    print("en lugar de pokemontcg.io")
    print("=" * 80)
    
    # 1. Obtener mapeo de sets
    set_mapping, tcgdex_sets = get_tcgdex_set_mapping()
    
    if not set_mapping:
        print("❌ No se pudo obtener el mapeo de sets")
        return
    
    # 2. Cargar archivos
    print("\nCargando archivos...")
    all_cards = load_json_file('all-cards.json')
    index_by_set = load_json_file('index-by-set.json')
    index_by_type = load_json_file('index-by-type.json')
    index_by_name = load_json_file('index-by-name.json')
    metadata = load_json_file('cards-metadata.json')
    
    print(f"Total de cartas: {len(all_cards):,}")
    
    # 3. Actualizar imágenes
    print("\n" + "=" * 80)
    print("Actualizando URLs de imágenes...")
    print("=" * 80)
    
    print("\n1. Actualizando all-cards.json...")
    updated_all = update_card_images(all_cards, set_mapping)
    print(f"   ✓ {updated_all:,} cartas actualizadas")
    
    print("\n2. Actualizando index-by-set.json...")
    updated_set = 0
    for set_id, cards in index_by_set.items():
        updated_set += update_card_images(cards, set_mapping)
    print(f"   ✓ {updated_set:,} cartas actualizadas")
    
    print("\n3. Actualizando index-by-type.json...")
    updated_type = 0
    for card_type, cards in index_by_type.items():
        updated_type += update_card_images(cards, set_mapping)
    print(f"   ✓ {updated_type:,} cartas actualizadas")
    
    print("\n4. Actualizando index-by-name.json...")
    updated_name = 0
    for name, cards in index_by_name.items():
        updated_name += update_card_images(cards, set_mapping)
    print(f"   ✓ {updated_name:,} cartas actualizadas")
    
    # 4. Actualizar metadata
    metadata['lastUpdated'] = datetime.now().isoformat() + 'Z'
    
    # 5. Guardar archivos
    print("\n" + "=" * 80)
    print("Guardando archivos...")
    print("=" * 80)
    
    save_json_file('all-cards.json', all_cards)
    save_json_file('index-by-set.json', index_by_set)
    save_json_file('index-by-type.json', index_by_type)
    save_json_file('index-by-name.json', index_by_name)
    save_json_file('cards-metadata.json', metadata)
    
    # 6. Resumen
    print("\n" + "=" * 80)
    print("✅ MIGRACIÓN COMPLETADA")
    print("=" * 80)
    print(f"Cartas actualizadas en all-cards.json: {updated_all:,}")
    print(f"Cartas actualizadas en index-by-set.json: {updated_set:,}")
    print(f"Cartas actualizadas en index-by-type.json: {updated_type:,}")
    print(f"Cartas actualizadas en index-by-name.json: {updated_name:,}")
    print(f"\nTotal de cartas en la base de datos: {len(all_cards):,}")
    print(f"Última actualización: {metadata['lastUpdated']}")
    
    print("\n🖼️  Nuevo formato de imágenes:")
    print("  • Proveedor: TCGdex")
    print("  • Small (245x337): {base_url}/low.jpg")
    print("  • Large (600x825): {base_url}/high.jpg")
    print("  • Sin reverso de carta")
    
    # Mostrar ejemplos
    print("\n📋 Ejemplos de URLs actualizadas:")
    import random
    sample_cards = random.sample([c for c in all_cards if 'images' in c], min(3, len(all_cards)))
    for card in sample_cards:
        print(f"\n  {card['name']} (Set: {card.get('set', {}).get('id', 'N/A')})")
        print(f"    {card['images']['large']}")
    
    print("=" * 80)

if __name__ == "__main__":
    main()
