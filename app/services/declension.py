"""
Russian name declension service using pymorphy3.
Provides declension of names to all Russian grammatical cases.
"""

from typing import Dict, Optional

import pymorphy3


class DeclensionService:
    """
    Russian name declension service using pymorphy3.
    
    Supports all six Russian grammatical cases:
    - Именительный (nominative): кто? что?
    - Родительный (genitive): кого? чего?
    - Дательный (dative): кому? чему?
    - Винительный (accusative): кого? что?
    - Творительный (instrumental): кем? чем?
    - Предложный (prepositional): о ком? о чём?
    """
    
    # Mapping of case names to pymorphy3 grammemes
    CASES = {
        'nominative': 'nomn',      # Именительный (кто? что?)
        'genitive': 'gent',        # Родительный (кого? чего?)
        'dative': 'datv',          # Дательный (кому? чему?)
        'accusative': 'accs',      # Винительный (кого? что?)
        'instrumental': 'ablt',    # Творительный (кем? чем?)
        'prepositional': 'loct'    # Предложный (о ком? о чём?)
    }
    
    # Russian case names for display
    CASE_NAMES_RU = {
        'nominative': 'Именительный',
        'genitive': 'Родительный',
        'dative': 'Дательный',
        'accusative': 'Винительный',
        'instrumental': 'Творительный',
        'prepositional': 'Предложный'
    }
    
    def __init__(self):
        """Initialize the morphology analyzer."""
        self.morph = pymorphy3.MorphAnalyzer()
        self._cache = {}  # Cache for performance
    
    def decline_word(self, word: str, case: str, gender: str = None) -> str:
        """
        Decline a single word to the specified grammatical case.
        
        Args:
            word: The word to decline
            case: Case name ('nominative', 'genitive', 'dative', 
                  'accusative', 'instrumental', 'prepositional')
            gender: Optional gender hint ('M' - male, 'F' - female, 'U' - undeclinable)
        
        Returns:
            Declined word preserving original capitalization
        """
        if not word or not word.strip():
            return ""
        
        word = word.strip()
        
        # If gender is 'U' (undeclinable), return word as-is
        if gender == 'U':
            return word
        
        # Check cache
        cache_key = (word.lower(), case, gender)
        if cache_key in self._cache:
            result = self._cache[cache_key]
            # Restore original capitalization
            if word[0].isupper():
                result = result.title()
            return result
        
        # Get case grammeme
        case_grammeme = self.CASES.get(case)
        if not case_grammeme:
            return word
        
        try:
            # Parse the word
            parsed_variants = self.morph.parse(word)
            
            # Try to find variant matching the specified gender
            parsed = None
            if gender:
                gender_grammeme = 'masc' if gender == 'M' else 'femn' if gender == 'F' else None
                if gender_grammeme:
                    for variant in parsed_variants:
                        if gender_grammeme in variant.tag:
                            parsed = variant
                            break
            
            # Fallback to first variant if no gender match
            if parsed is None:
                parsed = parsed_variants[0]
            
            # Try to inflect to the target case with gender hint
            if gender:
                gender_grammeme = 'masc' if gender == 'M' else 'femn' if gender == 'F' else None
                if gender_grammeme:
                    inflected = parsed.inflect({case_grammeme, gender_grammeme})
                    if not inflected:
                        inflected = parsed.inflect({case_grammeme})
                else:
                    inflected = parsed.inflect({case_grammeme})
            else:
                inflected = parsed.inflect({case_grammeme})
            
            if inflected:
                result = inflected.word
                # Cache the lowercase result
                self._cache[cache_key] = result
                
                # Restore original capitalization
                if word[0].isupper():
                    result = result.title()
                return result
        except Exception:
            pass
        
        return word
    
    def decline_full_name(
        self, 
        last_name: str, 
        first_name: str, 
        middle_name: Optional[str], 
        case: str,
        gender: str = None
    ) -> str:
        """
        Decline a full name (ФИО) to the specified case.
        
        Args:
            last_name: Фамилия
            first_name: Имя
            middle_name: Отчество (optional)
            case: Target grammatical case
            gender: Gender hint ('M' - male, 'F' - female, 'U' - undeclinable)
        
        Returns:
            Declined full name as "Фамилия Имя Отчество"
        """
        parts = [
            self.decline_word(last_name, case, gender),
            self.decline_word(first_name, case, gender),
        ]
        
        if middle_name:
            parts.append(self.decline_word(middle_name, case, gender))
        
        return " ".join(filter(None, parts))
    
    def get_all_declensions(
        self, 
        last_name: str, 
        first_name: str, 
        middle_name: Optional[str] = None,
        gender: str = None
    ) -> Dict[str, str]:
        """
        Get all case declensions for a name.
        Returns a dictionary with all template variables.
        
        Args:
            last_name: Фамилия
            first_name: Имя
            middle_name: Отчество (optional)
            gender: Gender hint ('M' - male, 'F' - female, 'U' - undeclinable)
        
        Returns:
            Dictionary with all declension variants for templates:
            - full_name, full_name_genitive, full_name_dative, etc.
            - last_name, last_name_genitive, etc.
            - first_name, first_name_genitive, etc.
            - middle_name, middle_name_genitive, etc.
            - initials, initials_before
        """
        result = {}
        
        # Generate all case declensions
        for case_name in self.CASES.keys():
            # Full name in each case
            result[f'full_name_{case_name}'] = self.decline_full_name(
                last_name, first_name, middle_name, case_name, gender
            )
            
            # Individual name parts in each case
            result[f'last_name_{case_name}'] = self.decline_word(last_name, case_name, gender)
            result[f'first_name_{case_name}'] = self.decline_word(first_name, case_name, gender)
            
            if middle_name:
                result[f'middle_name_{case_name}'] = self.decline_word(middle_name, case_name, gender)
            else:
                result[f'middle_name_{case_name}'] = ""
        
        # Default nominative case (without suffix)
        result['full_name'] = f"{last_name} {first_name}"
        if middle_name:
            result['full_name'] += f" {middle_name}"
        result['full_name'] = result['full_name'].strip()
        
        result['last_name'] = last_name or ''
        result['first_name'] = first_name or ''
        result['middle_name'] = middle_name or ''
        
        # Initials
        fi = first_name[0] if first_name else ""
        mi = middle_name[0] if middle_name else ""
        
        # Initials after surname: "Иванов И.И."
        if mi:
            result['initials'] = f"{last_name} {fi}.{mi}."
        else:
            result['initials'] = f"{last_name} {fi}."
        
        # Initials before surname: "И.И. Иванов"
        if mi:
            result['initials_before'] = f"{fi}.{mi}. {last_name}"
        else:
            result['initials_before'] = f"{fi}. {last_name}"
        
        return result
    
    def clear_cache(self):
        """Clear the declension cache."""
        self._cache.clear()
    
    def get_case_info(self, case: str) -> Dict[str, str]:
        """
        Get information about a grammatical case.
        
        Args:
            case: Case name in English
            
        Returns:
            Dictionary with case information
        """
        return {
            'name_en': case,
            'name_ru': self.CASE_NAMES_RU.get(case, case),
            'grammeme': self.CASES.get(case, '')
        }


# Singleton instance for convenience
_declension_service = None


def get_declension_service() -> DeclensionService:
    """Get or create the singleton declension service instance."""
    global _declension_service
    if _declension_service is None:
        _declension_service = DeclensionService()
    return _declension_service
