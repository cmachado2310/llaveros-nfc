"""
Repositorio y persistencia de proyectos (.nfcito).
Maneja guardado, carga, duplicación y validación de rutas de imágenes.
"""
import json
import shutil
import os
import time
from pathlib import Path
from typing import Optional, List, Tuple

from nfcito.models.project import Project, PieceDesign

class ProjectRepository:
    @staticmethod
    def save_project(project: Project, file_path: str, bundle_assets: bool = True) -> str:
        """
        Guarda el proyecto en un archivo .nfcito (JSON).
        Si bundle_assets es True, copia las imágenes a una carpeta 'assets' junto al archivo
        para que el proyecto no dependa de rutas temporales o externas.
        """
        target_path = Path(file_path).resolve()
        if target_path.suffix.lower() != ".nfcito":
            target_path = target_path.with_suffix(".nfcito")

        target_path.parent.mkdir(parents=True, exist_ok=True)
        assets_dir = target_path.parent / f"{target_path.stem}_assets"

        if bundle_assets:
            assets_dir.mkdir(parents=True, exist_ok=True)
            for piece_key, piece in project.pieces.items():
                if piece.image_path and os.path.exists(piece.image_path):
                    orig = Path(piece.image_path)
                    # Si ya está dentro de assets_dir, no volver a copiar
                    if orig.parent.resolve() != assets_dir.resolve():
                        dest = assets_dir / f"{piece_key}_{orig.name}"
                        shutil.copy2(orig, dest)
                        piece.image_path = str(dest)

        project.updated_at = time.time()
        project.file_path = str(target_path)

        data = project.to_dict()
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return str(target_path)

    @staticmethod
    def load_project(file_path: str) -> Tuple[Project, List[str]]:
        """
        Carga un proyecto desde un archivo .nfcito o .json.
        Localiza y recupera automáticamente todos los assets e imágenes en carpetas asociadas.
        Retorna la tupla (project, missing_images_warnings).
        """
        path = Path(file_path).resolve()
        if not path.exists():
            # Intentar con extensiones comunes
            if path.with_suffix(".nfcito").exists():
                path = path.with_suffix(".nfcito")
            elif path.with_suffix(".json").exists():
                path = path.with_suffix(".json")
            else:
                raise FileNotFoundError(f"El archivo de proyecto no existe: {file_path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        project = Project.from_dict(data, file_path=str(path))
        missing_images = []

        # Carpetas candidatas donde pueden residir los assets del proyecto
        candidate_dirs = [
            path.parent / f"{path.stem}_assets",
            path.parent / f"{path.name}_assets",
            path.parent / "assets",
            path.parent,
        ]

        # Verificar y resolver disponibilidad de imágenes para cada pieza
        for piece_key, piece in project.pieces.items():
            resolved_img: Optional[str] = None

            if piece.image_path:
                img_path = Path(piece.image_path)
                if img_path.exists():
                    resolved_img = str(img_path)
                else:
                    # Buscar en carpetas candidatas de assets
                    for c_dir in candidate_dirs:
                        if not c_dir.exists() or not c_dir.is_dir():
                            continue

                        # 1. Coincidencia exacta de nombre de archivo
                        if (c_dir / img_path.name).exists():
                            resolved_img = str(c_dir / img_path.name)
                            break

                        # 2. Nombre con prefijo de pieza (ej: portada_foto.jpg)
                        if (c_dir / f"{piece_key}_{img_path.name}").exists():
                            resolved_img = str(c_dir / f"{piece_key}_{img_path.name}")
                            break

                        # 3. Nombre sin prefijo de pieza si ya lo tenía
                        if img_path.name.startswith(f"{piece_key}_"):
                            stripped_name = img_path.name[len(piece_key) + 1:]
                            if (c_dir / stripped_name).exists():
                                resolved_img = str(c_dir / stripped_name)
                                break

                        # 4. Cualquier archivo en c_dir que empiece con el prefijo de la pieza
                        matching_prefix = list(c_dir.glob(f"{piece_key}_*"))
                        if matching_prefix:
                            # Filtrar solo archivos con extensión de imagen válida
                            valid_imgs = [p for p in matching_prefix if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".bmp")]
                            if valid_imgs:
                                resolved_img = str(valid_imgs[0])
                                break

                        # 5. Coincidencia por stem del archivo
                        matching_stem = list(c_dir.glob(f"*{img_path.stem}*"))
                        valid_stem_imgs = [p for p in matching_stem if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".bmp")]
                        if valid_stem_imgs:
                            resolved_img = str(valid_stem_imgs[0])
                            break

            # Si aún no tiene imagen asignada o no se encontró, buscar en los assets por prefijo de la pieza
            if not resolved_img:
                for c_dir in candidate_dirs:
                    if c_dir.exists() and c_dir.is_dir():
                        matching = list(c_dir.glob(f"{piece_key}_*"))
                        valid_imgs = [p for p in matching if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".bmp")]
                        if valid_imgs:
                            resolved_img = str(valid_imgs[0])
                            break

            if resolved_img:
                piece.image_path = resolved_img
            elif piece.image_path:
                missing_images.append(f"Pieza '{piece_key}': Imagen no encontrada ({Path(piece.image_path).name})")

        return project, missing_images

    @staticmethod
    def duplicate_project(source_file: str, new_name: str, new_file_path: str) -> str:
        """Duplica un proyecto existente con un nuevo nombre."""
        project, _ = ProjectRepository.load_project(source_file)
        project.name = new_name
        return ProjectRepository.save_project(project, new_file_path, bundle_assets=True)
