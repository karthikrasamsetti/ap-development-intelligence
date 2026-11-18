"""Initial sourced developments schema and illustrative demo rows.

Revision ID: 0001_initial
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('sources',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('url', sa.Text(), nullable=False, unique=True),
        sa.Column('published_on', sa.Date()),
        sa.Column('source_type', sa.String(30), nullable=False),
    )
    op.create_table('developments',
        sa.Column('id', sa.String(60), primary_key=True),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('category', sa.String(40), nullable=False),
        sa.Column('district', sa.String(100)),
        sa.Column('sector', sa.String(100)),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('investment_inr_crore', sa.Numeric(16, 2)),
        sa.Column('expected_jobs', sa.Integer()),
        sa.Column('jobs_created', sa.Integer()),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('source_id', sa.Integer(), sa.ForeignKey('sources.id')),
        sa.Column('is_demo', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('verification_status', sa.String(30), nullable=False, server_default='unverified'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_developments_category', 'developments', ['category'])
    op.create_index('ix_developments_district', 'developments', ['district'])
    op.create_index('ix_developments_status', 'developments', ['status'])
    op.bulk_insert(sa.table('developments',
        sa.column('id', sa.String), sa.column('title', sa.String), sa.column('category', sa.String),
        sa.column('district', sa.String), sa.column('sector', sa.String), sa.column('status', sa.String),
        sa.column('investment_inr_crore', sa.Numeric), sa.column('expected_jobs', sa.Integer),
        sa.column('summary', sa.Text), sa.column('is_demo', sa.Boolean), sa.column('verification_status', sa.String)), [
        {'id':'demo-001','title':'Illustrative renewable energy project','category':'investment','district':'Anantapur','sector':'Renewable energy','status':'mou_signed','investment_inr_crore':1200,'expected_jobs':850,'summary':'Illustrative record, not a real investment claim.','is_demo':True,'verification_status':'unverified'},
        {'id':'demo-002','title':'Illustrative port connectivity upgrade','category':'infrastructure','district':'Kakinada','sector':'Transport','status':'grounded','investment_inr_crore':450,'expected_jobs':200,'summary':'Illustrative record, not a real project claim.','is_demo':True,'verification_status':'unverified'},
        {'id':'demo-003','title':'Illustrative farmer support scheme','category':'scheme','district':None,'sector':'Agriculture','status':'approved','investment_inr_crore':None,'expected_jobs':None,'summary':'Illustrative statewide scheme, not an actual benefit claim.','is_demo':True,'verification_status':'unverified'},
    ])

def downgrade():
    op.drop_index('ix_developments_status', table_name='developments')
    op.drop_index('ix_developments_district', table_name='developments')
    op.drop_index('ix_developments_category', table_name='developments')
    op.drop_table('developments')
    op.drop_table('sources')
