"""
Golden Dataset Service
Parses the golden dataset PDF and compares it with generated test cases
"""
import re
from pathlib import Path
from typing import List, Dict, Optional
import PyPDF2
from difflib import SequenceMatcher


class GoldenDatasetService:
    def __init__(self, pdf_path: str = "Sample-TestCases_HotelApplication.pdf"):
        self.pdf_path = Path(pdf_path)
        self.golden_test_cases: List[Dict] = []
        if self.pdf_path.exists():
            self._parse_pdf()
    
    def _parse_pdf(self):
        """Parse the PDF and extract test cases"""
        try:
            with open(self.pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
                
                self._extract_test_cases(text)
        except Exception as e:
            print(f"[GoldenDatasetService] Error parsing PDF: {e}")
    
    def _extract_test_cases(self, text: str):
        """Extract test cases from PDF text"""
        # Split by test case IDs (e.g., US01-TC01, US02-TC01)
        pattern = r'(US\d+-TC\d+)'
        parts = re.split(pattern, text)
        
        current_ref_id = None
        for i, part in enumerate(parts):
            if re.match(pattern, part):
                current_ref_id = part
            elif current_ref_id and part.strip():
                # Extract title, steps, and expected result
                lines = [line.strip() for line in part.split('\n') if line.strip()]
                
                if len(lines) > 0:
                    title = lines[0] if lines else ""
                    
                    # Find steps section
                    steps = []
                    expected_result = ""
                    
                    in_steps = False
                    in_expected = False
                    
                    for line in lines[1:]:
                        if 'step' in line.lower() and ':' in line:
                            in_steps = True
                            in_expected = False
                            # Extract step content after the colon
                            step_content = line.split(':', 1)[1].strip() if ':' in line else line
                            if step_content:
                                steps.append(step_content)
                        elif 'expected' in line.lower() or 'result' in line.lower():
                            in_expected = True
                            in_steps = False
                            # Try to extract expected result from same line
                            if ':' in line:
                                expected_result = line.split(':', 1)[1].strip()
                        elif in_steps and line and not line.startswith(('US', 'TC')):
                            steps.append(line)
                        elif in_expected and line and not line.startswith(('US', 'TC')):
                            expected_result += " " + line
                    
                    self.golden_test_cases.append({
                        'ref_id': current_ref_id,
                        'title': title,
                        'steps': steps,
                        'expected_result': expected_result.strip()
                    })
                
                current_ref_id = None
        
        print(f"[GoldenDatasetService] Parsed {len(self.golden_test_cases)} golden test cases from PDF")
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts using SequenceMatcher"""
        if not text1 or not text2:
            return 0.0
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    def compare_test_case(self, test_case: Dict) -> Dict:
        """Compare a generated test case with golden dataset"""
        ref_id = test_case.get('test_case_ref_id') or test_case.get('ref_id') or test_case.get('scenario_ref_id', '')
        
        # Find matching golden test case by ref_id
        golden_tc = None
        for gtc in self.golden_test_cases:
            if gtc['ref_id'] == ref_id:
                golden_tc = gtc
                break
        
        if not golden_tc:
            return {
                'match_found': False,
                'similarity_percentage': 0.0,
                'details': 'No matching golden test case found'
            }
        
        # Calculate similarity scores
        title_similarity = self.calculate_similarity(
            test_case.get('title', ''),
            golden_tc['title']
        )
        
        # Compare steps
        generated_steps = test_case.get('steps', [])
        golden_steps = golden_tc['steps']
        
        # Calculate average similarity for steps
        step_similarities = []
        max_steps = max(len(generated_steps), len(golden_steps))
        
        for i in range(max_steps):
            gen_step = generated_steps[i] if i < len(generated_steps) else ""
            gold_step = golden_steps[i] if i < len(golden_steps) else ""
            step_similarities.append(self.calculate_similarity(gen_step, gold_step))
        
        avg_step_similarity = sum(step_similarities) / len(step_similarities) if step_similarities else 0.0
        
        # Compare expected results
        expected_similarity = self.calculate_similarity(
            test_case.get('expected_result', ''),
            golden_tc['expected_result']
        )
        
        # Weighted average: title (20%), steps (60%), expected result (20%)
        overall_similarity = (
            title_similarity * 0.2 +
            avg_step_similarity * 0.6 +
            expected_similarity * 0.2
        )
        
        return {
            'match_found': True,
            'similarity_percentage': round(overall_similarity * 100, 1),
            'title_similarity': round(title_similarity * 100, 1),
            'steps_similarity': round(avg_step_similarity * 100, 1),
            'expected_result_similarity': round(expected_similarity * 100, 1),
            'golden_test_case': golden_tc
        }
    
    def get_golden_test_cases(self) -> List[Dict]:
        """Get all parsed golden test cases"""
        return self.golden_test_cases


# Singleton instance
_golden_dataset_service = None


def get_golden_dataset_service() -> GoldenDatasetService:
    """Get or create singleton instance"""
    global _golden_dataset_service
    if _golden_dataset_service is None:
        _golden_dataset_service = GoldenDatasetService()
    return _golden_dataset_service
