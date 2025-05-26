"""initial migration

Revision ID: 001
Revises: 
Create Date: 2024-03-26 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # users 테이블 생성
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('gender', sa.String(length=10), nullable=True),
        sa.Column('health_conditions', sa.Text(), nullable=True),
        sa.Column('allergies', sa.Text(), nullable=True),
        sa.Column('is_guest', sa.Boolean(), nullable=True),
        sa.Column('email', sa.String(length=100), nullable=True),
        sa.Column('hashed_password', sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # supplements 테이블 생성
    op.create_table(
        'supplements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('brand', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('target_gender', sa.String(length=10), nullable=True),
        sa.Column('target_age_range', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_supplements_id'), 'supplements', ['id'], unique=False)

    # ingredients 테이블 생성
    op.create_table(
        'ingredients',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('risk_info', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ingredients_id'), 'ingredients', ['id'], unique=False)

    # supplement_ingredients 테이블 생성
    op.create_table(
        'supplement_ingredients',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('supplement_id', sa.Integer(), nullable=True),
        sa.Column('ingredient_id', sa.Integer(), nullable=True),
        sa.Column('amount_mg', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['ingredient_id'], ['ingredients.id'], ),
        sa.ForeignKeyConstraint(['supplement_id'], ['supplements.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_supplement_ingredients_id'), 'supplement_ingredients', ['id'], unique=False)

    # interactions 테이블 생성
    op.create_table(
        'interactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('ingredient_id_1', sa.Integer(), nullable=True),
        sa.Column('ingredient_id_2', sa.Integer(), nullable=True),
        sa.Column('interaction_type', sa.String(length=50), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['ingredient_id_1'], ['ingredients.id'], ),
        sa.ForeignKeyConstraint(['ingredient_id_2'], ['ingredients.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_interactions_id'), 'interactions', ['id'], unique=False)

    # llm_requests 테이블 생성
    op.create_table(
        'llm_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('input_prompt', sa.Text(), nullable=True),
        sa.Column('llm_response', sa.Text(), nullable=True),
        sa.Column('model', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_llm_requests_id'), 'llm_requests', ['id'], unique=False)

    # recommendation_logs 테이블 생성
    op.create_table(
        'recommendation_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('recommended_supplement_id', sa.Integer(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['recommended_supplement_id'], ['supplements.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recommendation_logs_id'), 'recommendation_logs', ['id'], unique=False)

    # guest_sessions 테이블 생성
    op.create_table(
        'guest_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('session_id', sa.String(length=100), nullable=True),
        sa.Column('browser_fingerprint', sa.String(length=100), nullable=True),
        sa.Column('temporary_health_conditions', sa.Text(), nullable=True),
        sa.Column('temporary_allergies', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_guest_sessions_session_id'), 'guest_sessions', ['session_id'], unique=True)

    # guest_recommendation_logs 테이블 생성
    op.create_table(
        'guest_recommendation_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('session_id', sa.String(length=100), nullable=True),
        sa.Column('recommended_supplement_id', sa.Integer(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['recommended_supplement_id'], ['supplements.id'], ),
        sa.ForeignKeyConstraint(['session_id'], ['guest_sessions.session_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_guest_recommendation_logs_id'), 'guest_recommendation_logs', ['id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_guest_recommendation_logs_id'), table_name='guest_recommendation_logs')
    op.drop_table('guest_recommendation_logs')
    op.drop_index(op.f('ix_guest_sessions_session_id'), table_name='guest_sessions')
    op.drop_table('guest_sessions')
    op.drop_index(op.f('ix_recommendation_logs_id'), table_name='recommendation_logs')
    op.drop_table('recommendation_logs')
    op.drop_index(op.f('ix_llm_requests_id'), table_name='llm_requests')
    op.drop_table('llm_requests')
    op.drop_index(op.f('ix_interactions_id'), table_name='interactions')
    op.drop_table('interactions')
    op.drop_index(op.f('ix_supplement_ingredients_id'), table_name='supplement_ingredients')
    op.drop_table('supplement_ingredients')
    op.drop_index(op.f('ix_ingredients_id'), table_name='ingredients')
    op.drop_table('ingredients')
    op.drop_index(op.f('ix_supplements_id'), table_name='supplements')
    op.drop_table('supplements')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users') 