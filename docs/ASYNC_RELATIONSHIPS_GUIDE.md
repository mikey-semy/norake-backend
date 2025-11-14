# SQLAlchemy Async Relationships - Reference Guide

## Problem: MissingGreenlet Error

When using SQLAlchemy async sessions with relationships, accessing relationship attributes during Pydantic serialization causes:

```
MissingGreenlet: greenlet_spawn has not been called;
can't access lazy loaded attributes from async code
```

**Root Cause**: SQLAlchemy relationships in async mode require explicit loading. Pydantic's `model_validate()` tries to access relationships synchronously → error.

## Solution: Explicit Relationship Loading

After ANY repository operation that returns a model with relationships, load them explicitly:

```python
# Pattern: Load relationships BEFORE returning model
await self.repository.session.refresh(
    model_instance,
    attribute_names=["relationship1", "relationship2", ...]
)
```

## Implementation Checklist

### 1. Identify Models with Relationships

Look for models with `Mapped[...]` relationships:

```python
class DocumentServiceModel(BaseModel):
    # Scalar fields
    title: Mapped[str]

    # ⚠️ RELATIONSHIPS - need explicit loading
    author: Mapped["UserModel"] = relationship(...)
    workspace: Mapped[Optional["WorkspaceModel"]] = relationship(...)
```

### 2. Add Loading to Service Methods

For EVERY service method that returns the model:

#### ✅ CREATE Methods

```python
async def create_something(self, data: dict) -> SomeModel:
    # Create
    item = await self.repository.create_item(data)

    # Load relationships BEFORE returning
    await self.repository.session.refresh(
        item,
        attribute_names=["author", "workspace"]
    )

    return item
```

#### ✅ GET Methods

```python
async def get_something(self, item_id: UUID) -> SomeModel:
    # Get
    item = await self.repository.get_item_by_id(item_id)
    if not item:
        raise NotFoundError()

    # Load relationships
    await self.repository.session.refresh(
        item,
        attribute_names=["author", "workspace"]
    )

    return item
```

#### ✅ UPDATE Methods

```python
async def update_something(self, item_id: UUID, data: dict) -> SomeModel:
    # Update
    item = await self.repository.update_item(item_id, data)

    # Load relationships
    await self.repository.session.refresh(
        item,
        attribute_names=["author", "workspace"]
    )

    return item
```

#### ✅ LIST Methods

```python
async def list_something(self, filters: dict) -> List[SomeModel]:
    # Get list
    items = await self.repository.filter_by(**filters)

    # Load relationships FOR EACH item
    for item in items:
        await self.repository.session.refresh(
            item,
            attribute_names=["author", "workspace"]
        )

    return items
```

### 3. When Loading is NOT Needed

Skip relationship loading for methods that:
- Return scalar values (bool, str, int, UUID)
- Don't return the model at all (void methods)
- Return aggregated data (counts, sums)

```python
# ✅ No loading needed - returns bool
async def delete_something(self, item_id: UUID) -> bool:
    return await self.repository.delete_item(item_id)

# ✅ No loading needed - returns string
async def generate_qr(self, item_id: UUID) -> str:
    return await self.qr_service.generate(item_id)

# ✅ No loading needed - returns count
async def count_items(self) -> int:
    return await self.repository.count_items()
```

## Complete Example: Document Services

See `src/services/v1/document_services.py` for real-world implementation:

```python
# Method 1: Create
async def create_document_service(...) -> DocumentServiceModel:
    document_service = await self.repository.create_item(create_data)
    await self.repository.session.refresh(
        document_service,
        attribute_names=["author", "workspace"]
    )
    return document_service

# Method 2: Get
async def get_document_service(...) -> DocumentServiceModel:
    service = await self.repository.get_item_by_id(service_id)
    await self.repository.session.refresh(
        service,
        attribute_names=["author", "workspace"]
    )
    return service

# Method 3: Update
async def update_document_service(...) -> DocumentServiceModel:
    updated_service = await self.repository.update_item(...)
    await self.repository.session.refresh(
        updated_service,
        attribute_names=["author", "workspace"]
    )
    return updated_service

# Method 4: List
async def list_document_services(...) -> List[DocumentServiceModel]:
    services = await self._filter_services(query)
    for service in services:
        await self.repository.session.refresh(
            service,
            attribute_names=["author", "workspace"]
        )
    return services
```

## Testing Validation

To verify relationship loading works:

1. **Check Response Schema**: Response must include nested relationship data:
   ```json
   {
     "success": true,
     "data": {
       "id": "...",
       "title": "...",
       "author": {           // ← Must be populated
         "username": "admin",
         "email": "admin@example.com"
       }
     }
   }
   ```

2. **No MissingGreenlet Errors**: All endpoints should return 200 OK without:
   ```
   MissingGreenlet: greenlet_spawn has not been called
   ```

3. **Test All CRUD Operations**:
   - ✅ POST (create) - returns model with relationships
   - ✅ GET (read) - returns model with relationships
   - ✅ PUT/PATCH (update) - returns model with relationships
   - ✅ GET (list) - returns array of models with relationships
   - ✅ DELETE - returns bool (no relationships needed)

## Performance Considerations

**Single Refresh for Multiple Relationships**:
```python
# ✅ GOOD - Load all relationships in one call
await session.refresh(model, attribute_names=["author", "workspace", "tags"])

# ❌ BAD - Multiple refresh calls
await session.refresh(model, attribute_names=["author"])
await session.refresh(model, attribute_names=["workspace"])
await session.refresh(model, attribute_names=["tags"])
```

**Batch Loading for Lists**:
```python
# For large lists, consider selectinload in repository query
from sqlalchemy.orm import selectinload

query = select(Model).options(
    selectinload(Model.author),
    selectinload(Model.workspace)
)
# Then no refresh needed - relationships already loaded
```

## Quick Reference

| Operation | Needs Loading? | Why |
|-----------|----------------|-----|
| `create_item()` | ✅ YES | Returns model with relationships |
| `get_item_by_id()` | ✅ YES | Returns model with relationships |
| `update_item()` | ✅ YES | Returns model with relationships |
| `filter_by()` | ✅ YES (each item) | Returns list of models |
| `delete_item()` | ❌ NO | Returns bool |
| `count_items()` | ❌ NO | Returns int |
| Custom queries returning models | ✅ YES | Any model with relationships |

## Files Changed in Document Services Implementation

1. **src/models/v1/document_services.py** (lines 192-201):
   - Fixed enum type: `Mapped[str]` instead of `Mapped[DocumentFileType]`

2. **src/services/v1/document_services.py**:
   - `create_document_service` (lines 160-168)
   - `get_document_service` (lines 207-228)
   - `update_document_service` (lines 282-288)
   - `list_document_services` (lines 428-434)
   - `add_function` (lines 499-505)
   - `remove_function` (lines 565-571)
   - `get_most_viewed` (lines 656-664)

## Result

✅ **8/8 endpoints tested successfully** (100% pass rate)
✅ **All relationship serialization working**
✅ **No MissingGreenlet errors**
✅ **Task 13/13 complete**
