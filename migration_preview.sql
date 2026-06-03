alembic : INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
At line:1 char:1
+ alembic upgrade head --sql 2>&1 | Out-File -FilePath migration_previe ...
+ ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (INFO  [alembic....PostgresqlImpl.:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
 
INFO  [alembic.runtime.migration] Generating static SQL
INFO  [alembic.runtime.migration] Will assume transactional DDL.
BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

INFO  [alembic.runtime.migration] Running upgrade  -> 001, initial migration
-- Running upgrade  -> 001

CREATE TYPE itemtype AS ENUM ('SERVICE', 'PRODUCT');

CREATE TABLE item (
    id UUID NOT NULL, 
    slug VARCHAR NOT NULL, 
    title VARCHAR NOT NULL, 
    description TEXT, 
    item_type itemtype NOT NULL, 
    category VARCHAR NOT NULL, 
    thumbnail VARCHAR, 
    price_markup NUMERIC(12, 2) DEFAULT '0.00' NOT NULL, 
    currency VARCHAR(3) DEFAULT 'ZAR' NOT NULL, 
    delivery_time VARCHAR, 
    stock INTEGER, 
    is_visible BOOLEAN DEFAULT true NOT NULL, 
    is_archived BOOLEAN DEFAULT false NOT NULL, 
    meta JSON, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_item_slug ON item (slug);

CREATE TABLE provider (
    id UUID NOT NULL, 
    name VARCHAR NOT NULL, 
    base_url VARCHAR, 
    notes TEXT, 
    is_active BOOLEAN DEFAULT true NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (name)
);

CREATE TYPE userrole AS ENUM ('CLIENT', 'ADMIN');

CREATE TABLE "user" (
    id UUID NOT NULL, 
    email VARCHAR NOT NULL, 
    password_hash VARCHAR NOT NULL, 
    role userrole DEFAULT 'CLIENT' NOT NULL, 
    is_active BOOLEAN DEFAULT true NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_user_email ON "user" (email);

CREATE TYPE orderstatus AS ENUM ('PENDING', 'PAID', 'FULFILLED', 'CANCELLED', 'REFUNDED');

CREATE TABLE "order" (
    id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    status orderstatus DEFAULT 'PENDING' NOT NULL, 
    payment_ref VARCHAR, 
    payment_gateway VARCHAR, 
    total_amount NUMERIC(12, 2) NOT NULL, 
    currency VARCHAR(3) DEFAULT 'ZAR' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id)
);

CREATE TABLE orderitem (
    id UUID NOT NULL, 
    order_id UUID NOT NULL, 
    item_id UUID NOT NULL, 
    quantity INTEGER NOT NULL, 
    unit_price NUMERIC(12, 2) NOT NULL, 
    PRIMARY KEY (id)
);

CREATE TABLE credential (
    id UUID NOT NULL, 
    item_id UUID NOT NULL, 
    payload TEXT NOT NULL, 
    is_used BOOLEAN DEFAULT false NOT NULL, 
    order_item_id UUID, 
    assigned_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id)
);

CREATE TABLE providerlisting (
    id UUID NOT NULL, 
    item_id UUID NOT NULL, 
    provider_id UUID NOT NULL, 
    external_id VARCHAR, 
    cost_price NUMERIC(12, 2) NOT NULL, 
    is_preferred BOOLEAN DEFAULT false NOT NULL, 
    is_active BOOLEAN DEFAULT true NOT NULL, 
    PRIMARY KEY (id)
);

ALTER TABLE "order" ADD CONSTRAINT fk_order_user_id FOREIGN KEY(user_id) REFERENCES "user" (id);

ALTER TABLE orderitem ADD CONSTRAINT fk_orderitem_order_id FOREIGN KEY(order_id) REFERENCES "order" (id);

ALTER TABLE orderitem ADD CONSTRAINT fk_orderitem_item_id FOREIGN KEY(item_id) REFERENCES item (id);

ALTER TABLE credential ADD CONSTRAINT fk_credential_item_id FOREIGN KEY(item_id) REFERENCES item (id);

ALTER TABLE credential ADD CONSTRAINT fk_credential_order_item_id FOREIGN KEY(order_item_id) REFERENCES orderitem (id);

ALTER TABLE providerlisting ADD CONSTRAINT fk_providerlisting_item_id FOREIGN KEY(item_id) REFERENCES item (id);

ALTER TABLE providerlisting ADD CONSTRAINT fk_providerlisting_provider_id FOREIGN KEY(provider_id) REFERENCES provider (id);

INSERT INTO alembic_version (version_num) VALUES ('001') RETURNING alembic_version.version_num;

COMMIT;

