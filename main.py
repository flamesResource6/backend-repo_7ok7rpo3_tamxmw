import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId
from typing import List, Optional

from database import db, create_document, get_documents
from schemas import Application, StatusUpdate, Department, User, Notification, AppFilter

app = FastAPI(title="College Digital Application Management System API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "CDAMS Backend Running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# ---------- Helpers ----------
class IdModel(BaseModel):
    id: str


def to_public(doc):
    if not doc:
        return doc
    doc["id"] = str(doc.pop("_id"))
    return doc


# ---------- Reference Data Endpoints ----------
@app.post("/departments", response_model=dict)
async def create_department(dept: Department):
    inserted_id = create_document("department", dept)
    return {"id": inserted_id}


@app.get("/departments", response_model=List[dict])
async def list_departments():
    docs = get_documents("department")
    return [to_public(d) for d in docs]


@app.post("/users", response_model=dict)
async def create_user(user: User):
    inserted_id = create_document("user", user)
    return {"id": inserted_id}


@app.get("/users", response_model=List[dict])
async def list_users():
    docs = get_documents("user")
    return [to_public(d) for d in docs]


# ---------- Applications Flow ----------
@app.post("/applications", response_model=dict)
async def submit_application(app_data: Application):
    inserted_id = create_document("application", app_data)
    # Initial status update
    su = StatusUpdate(
        application_id=inserted_id,
        actor_role="student",
        actor_name=app_data.student_name,
        action="submit",
        comments="Application submitted",
    )
    create_document("statusupdate", su)
    return {"id": inserted_id, "status": "submitted"}


@app.get("/applications", response_model=List[dict])
async def list_applications(student_id: Optional[str] = None, department_code: Optional[str] = None, status: Optional[str] = None, category: Optional[str] = None):
    filt = {}
    if student_id:
        filt["student_id"] = student_id
    if department_code:
        filt["department_code"] = department_code
    if status:
        filt["status"] = status
    if category:
        filt["category"] = category
    docs = get_documents("application", filt)
    return [to_public(d) for d in docs]


class ReviewAction(BaseModel):
    actor_role: str
    actor_name: str
    action: str  # forward | approve | reject | review
    comments: Optional[str] = None
    to_department: Optional[str] = None


@app.post("/applications/{app_id}/action", response_model=dict)
async def act_on_application(app_id: str, action: ReviewAction):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    # validate app exists
    doc = db["application"].find_one({"_id": ObjectId(app_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Application not found")

    # Update status based on action
    new_status = doc.get("status", "submitted")
    current_stage = doc.get("current_stage", "coordinator")

    if action.action == "forward":
        new_status = "forwarded"
        current_stage = action.to_department or current_stage
        db["application"].update_one({"_id": ObjectId(app_id)}, {"$set": {"status": new_status, "current_stage": current_stage}, "$push": {"route_history": current_stage}})
    elif action.action == "approve":
        new_status = "approved"
        db["application"].update_one({"_id": ObjectId(app_id)}, {"$set": {"status": new_status}})
    elif action.action == "reject":
        new_status = "rejected"
        db["application"].update_one({"_id": ObjectId(app_id)}, {"$set": {"status": new_status}})
    else:
        new_status = "under_review"
        db["application"].update_one({"_id": ObjectId(app_id)}, {"$set": {"status": new_status}})

    # Log status update
    su = StatusUpdate(
        application_id=app_id,
        actor_role=action.actor_role, actor_name=action.actor_name,
        action=action.action, comments=action.comments, to_department=action.to_department
    )
    create_document("statusupdate", su)

    return {"id": app_id, "status": new_status, "current_stage": current_stage}


@app.get("/applications/{app_id}/timeline", response_model=List[dict])
async def get_timeline(app_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    docs = list(db["statusupdate"].find({"application_id": app_id}).sort("created_at", 1))
    return [to_public(d) for d in docs]


# ---------- Notifications ----------
@app.post("/notifications", response_model=dict)
async def notify(note: Notification):
    inserted_id = create_document("notification", note)
    return {"id": inserted_id}


@app.get("/notifications", response_model=List[dict])
async def list_notifications(user_email: Optional[str] = None):
    filt = {"user_email": user_email} if user_email else {}
    docs = get_documents("notification", filt)
    return [to_public(d) for d in docs]


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
