from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import sqlite3
from datetime import datetime
import json

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

# Выбор базы данных: PostgreSQL (на Render) или SQLite (локально)
def get_db_connection():
    database_url = os.getenv('DATABASE_URL')
    
    if database_url:
        # PostgreSQL (на Render)
        import psycopg2
        import psycopg2.extras
        
        # Парсим DATABASE_URL
        # postgresql://user:password@host:port/database
        conn = psycopg2.connect(database_url)
        conn.row_factory = psycopg2.extras.RealDictCursor
        return conn
    else:
        # SQLite (локально)
        conn = sqlite3.connect("database.db")
        conn.row_factory = sqlite3.Row
        return conn

# Инициализация базы данных
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Проверяем, PostgreSQL или SQLite
    if os.getenv('DATABASE_URL'):
        # PostgreSQL
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recipes (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                ingredients TEXT NOT NULL,
                instructions TEXT NOT NULL,
                category TEXT NOT NULL,
                time INTEGER NOT NULL,
                image TEXT
            )
        """)
    else:
        # SQLite
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
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recipes ORDER BY id DESC")
    
    if os.getenv('DATABASE_URL'):
        # PostgreSQL
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append(dict(row))
    else:
        # SQLite
        rows = cursor.fetchall()
        result = [dict(row) for row in rows]
    
    conn.close()
    return result

@app.post("/api/recipes")
async def create_recipe(recipe: Recipe):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if os.getenv('DATABASE_URL'):
        # PostgreSQL
        cursor.execute(
            "INSERT INTO recipes (name, ingredients, instructions, category, time, image) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (recipe.name, recipe.ingredients, recipe.instructions, recipe.category, recipe.time, recipe.image)
        )
        recipe_id = cursor.fetchone()['id']
    else:
        # SQLite
        cursor.execute(
            "INSERT INTO recipes (name, ingredients, instructions, category, time, image) VALUES (?, ?, ?, ?, ?, ?)",
            (recipe.name, recipe.ingredients, recipe.instructions, recipe.category, recipe.time, recipe.image)
        )
        recipe_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    return {"id": recipe_id, **recipe.dict()}

@app.put("/api/recipes/{recipe_id}")
async def update_recipe(recipe_id: int, recipe: RecipeUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Проверяем существование
    cursor.execute("SELECT * FROM recipes WHERE id = %s" if os.getenv('DATABASE_URL') else "SELECT * FROM recipes WHERE id = ?", (recipe_id,))
    existing = cursor.fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    # Обновляем только переданные поля
    updates = []
    values = []
    if recipe.name is not None:
        updates.append("name = %s" if os.getenv('DATABASE_URL') else "name = ?")
        values.append(recipe.name)
    if recipe.ingredients is not None:
        updates.append("ingredients = %s" if os.getenv('DATABASE_URL') else "ingredients = ?")
        values.append(recipe.ingredients)
    if recipe.instructions is not None:
        updates.append("instructions = %s" if os.getenv('DATABASE_URL') else "instructions = ?")
        values.append(recipe.instructions)
    if recipe.category is not None:
        updates.append("category = %s" if os.getenv('DATABASE_URL') else "category = ?")
        values.append(recipe.category)
    if recipe.time is not None:
        updates.append("time = %s" if os.getenv('DATABASE_URL') else "time = ?")
        values.append(recipe.time)
    if recipe.image is not None:
        updates.append("image = %s" if os.getenv('DATABASE_URL') else "image = ?")
        values.append(recipe.image)
    
    if not updates:
        conn.close()
        return {"message": "No fields to update"}
    
    values.append(recipe_id)
    query = f"UPDATE recipes SET {', '.join(updates)} WHERE id = %s" if os.getenv('DATABASE_URL') else f"UPDATE recipes SET {', '.join(updates)} WHERE id = ?"
    cursor.execute(query, values)
    conn.commit()
    conn.close()
    
    return {"id": recipe_id, "message": "Recipe updated"}

@app.delete("/api/recipes/{recipe_id}")
async def delete_recipe(recipe_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM recipes WHERE id = %s" if os.getenv('DATABASE_URL') else "DELETE FROM recipes WHERE id = ?", (recipe_id,))
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