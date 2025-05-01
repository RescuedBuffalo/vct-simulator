"""Initial migration

Revision ID: initial
Revises: 
Create Date: 2023-11-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create matches table
    op.create_table('matches',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('map_name', sa.String(), nullable=True),
        sa.Column('team_a_score', sa.Integer(), nullable=True),
        sa.Column('team_b_score', sa.Integer(), nullable=True),
        sa.Column('current_round', sa.Integer(), nullable=True),
        sa.Column('is_overtime', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_matches_id'), 'matches', ['id'], unique=False)

    # Create teams table
    op.create_table('teams',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('match_id', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('side', sa.String(), nullable=True),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['match_id'], ['matches.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_teams_id'), 'teams', ['id'], unique=False)

    # Create players table
    op.create_table('players',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('match_id', sa.String(), nullable=True),
        sa.Column('team_id', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('agent', sa.String(), nullable=True),
        sa.Column('role', sa.String(), nullable=True),
        sa.Column('aim_rating', sa.Float(), nullable=True),
        sa.Column('reaction_time', sa.Float(), nullable=True),
        sa.Column('movement_accuracy', sa.Float(), nullable=True),
        sa.Column('spray_control', sa.Float(), nullable=True),
        sa.Column('clutch_iq', sa.Float(), nullable=True),
        sa.Column('health', sa.Integer(), nullable=True),
        sa.Column('armor', sa.Integer(), nullable=True),
        sa.Column('credits', sa.Integer(), nullable=True),
        sa.Column('weapon', sa.String(), nullable=True),
        sa.Column('shield', sa.String(), nullable=True),
        sa.Column('alive', sa.Boolean(), nullable=True),
        sa.Column('location', sqlite.JSON(), nullable=True),
        sa.Column('ai_type', sa.String(), nullable=True),
        sa.Column('ai_skill_level', sa.Float(), nullable=True),
        sa.Column('kills', sa.Integer(), nullable=True),
        sa.Column('deaths', sa.Integer(), nullable=True),
        sa.Column('assists', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['match_id'], ['matches.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_players_id'), 'players', ['id'], unique=False)

    # Create rounds table
    op.create_table('rounds',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('match_id', sa.String(), nullable=True),
        sa.Column('round_number', sa.Integer(), nullable=True),
        sa.Column('phase', sa.String(), nullable=True),
        sa.Column('time_remaining', sa.Float(), nullable=True),
        sa.Column('spike_planted', sa.Boolean(), nullable=True),
        sa.Column('spike_time_remaining', sa.Float(), nullable=True),
        sa.Column('winner', sa.String(), nullable=True),
        sa.Column('end_condition', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['match_id'], ['matches.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rounds_id'), 'rounds', ['id'], unique=False)

    # Create round_events table
    op.create_table('round_events',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('round_id', sa.String(), nullable=True),
        sa.Column('event_type', sa.String(), nullable=True),
        sa.Column('timestamp', sa.Float(), nullable=True),
        sa.Column('data', sqlite.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['round_id'], ['rounds.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_round_events_id'), 'round_events', ['id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_round_events_id'), table_name='round_events')
    op.drop_table('round_events')
    op.drop_index(op.f('ix_rounds_id'), table_name='rounds')
    op.drop_table('rounds')
    op.drop_index(op.f('ix_players_id'), table_name='players')
    op.drop_table('players')
    op.drop_index(op.f('ix_teams_id'), table_name='teams')
    op.drop_table('teams')
    op.drop_index(op.f('ix_matches_id'), table_name='matches')
    op.drop_table('matches') 