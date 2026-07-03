from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sqlite3
import os

app = FastAPI(title="Recipe API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Модель данных
class Recipe(BaseModel):
    name: str
    ingredients: str
    instructions: str
    category: str
    time: int
    image: Optional[str] = None

class RecipeUpdate(BaseModel):
    name: Optional[str] = None
    ingredients: Optional[str] = None
    instructions: Optional[str] = None
    category: Optional[str] = None
    time: Optional[int] = None
    image: Optional[str] = None

# Подключение к SQLite
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# Инициализация базы данных
def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            ingredients TEXT NOT NULL,
            instructions TEXT NOT NULL,
            category TEXT NOT NULL,
            time INTEGER NOT NULL,
            image TEXT
        )
    """)
    conn.commit()
    conn.close()

# Создаем базу при запуске
init_db()

# Эндпоинты
@app.get("/api/recipes")
async def get_recipes():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recipes ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/api/recipes")
async def create_recipe(recipe: Recipe):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO recipes (name, ingredients, instructions, category, time, image) VALUES (?, ?, ?, ?, ?, ?)",
        (recipe.name, recipe.ingredients, recipe.instructions, recipe.category, recipe.time, recipe.image)
    )
    conn.commit()
    recipe_id = cursor.lastrowid
    conn.close()
    return {"id": recipe_id, **recipe.dict()}

@app.put("/api/recipes/{recipe_id}")
async def update_recipe(recipe_id: int, recipe: RecipeUpdate):
    conn = get_db()
    cursor = conn.cursor()
    
    # Проверяем существование
    cursor.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,))
    existing = cursor.fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    # Обновляем только переданные поля
    updates = []
    values = []
    if recipe.name is not None:
        updates.append("name = ?")
        values.append(recipe.name)
    if recipe.ingredients is not None:
        updates.append("ingredients = ?")
        values.append(recipe.ingredients)
    if recipe.instructions is not None:
        updates.append("instructions = ?")
        values.append(recipe.instructions)
    if recipe.category is not None:
        updates.append("category = ?")
        values.append(recipe.category)
    if recipe.time is not None:
        updates.append("time = ?")
        values.append(recipe.time)
    if recipe.image is not None:
        updates.append("image = ?")
        values.append(recipe.image)
    
    if not updates:
        conn.close()
        return {"message": "No fields to update"}
    
    values.append(recipe_id)
    query = f"UPDATE recipes SET {', '.join(updates)} WHERE id = ?"
    cursor.execute(query, values)
    conn.commit()
    conn.close()
    
    return {"id": recipe_id, "message": "Recipe updated"}

@app.delete("/api/recipes/{recipe_id}")
async def delete_recipe(recipe_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Recipe not found")
    conn.commit()
    conn.close()
    return {"message": "Recipe deleted"}

# Статика
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)