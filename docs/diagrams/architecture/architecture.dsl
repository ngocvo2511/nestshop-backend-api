workspace "E-commerce Backend API" "SRS v0.9: modular monolith with optional P1 email." {
    !impliedRelationships false

    model {
        guest = person "Guest" "Browses the public catalog and registers or logs in."
        customer = person "Customer" "Manages own profile, checkout, orders and payments."
        staff = person "Staff" "Inspects eligible orders and advances fulfillment."
        admin = person "Admin" "Manages catalog, stock and roles; inspects reconciliation."

        shop = softwareSystem "E-commerce Backend API" "REST API for accounts, catalog, stock-safe orders and verified sandbox payments." {
            backend = container "Backend Application" "Modular monolith for accounts, catalog, orders and payments. Includes in-process expiration jobs." "NestJS, TypeScript, TypeORM" {
                tags "Backend"
                auth = component "Auth" "Login, JWT access, refresh rotation and session revocation." "NestJS, JWT"
                users = component "Users" "Own profile, password changes and audited Admin role assignments." "NestJS module"
                products = component "Products" "Public catalog, Admin product changes and validated image uploads." "NestJS module, Multer"
                inventory = component "Inventory" "Stock reservation, release and audited Admin adjustments." "NestJS, TypeORM"
                orders = component "Orders" "Checkout, shipping snapshots, own history and staff fulfillment." "NestJS module"
                payments = component "Payments" "Signed URLs, verified idempotent IPN, browser return and reconciliation." "NestJS"
                expiration = component "ExpirationScheduler" "Startup and periodic attempt/order expiry scans." "In-process scheduler"
                health = component "Health" "Public lightweight API health check." "NestJS"
                categories = component "Categories (P1)" "Optional public category browsing and Admin CRUD." "NestJS" {
                    tags "Optional"
                }
                cart = component "Cart (P1)" "Optional customer-owned cart; no price or stock reservation." "NestJS" {
                    tags "Optional"
                }
                notifications = component "Notifications / Email (P1)" "Optional durable events, post-commit email and bounded recovery/retry." "NestJS, SMTP mailer" {
                    tags "Optional"
                }
            }
            database = container "PostgreSQL Database" "Business data, sessions and history/audits. Transactions protect stock and settlement." "PostgreSQL" {
                tags "Database"
            }
            files = container "Local File Storage" "Product images in a configurable directory mounted into the backend; not a separate service." "Local filesystem, Docker named volume" {
                tags "FileStorage"
            }
        }

        vnpay = softwareSystem "VNPay Sandbox" "External payment provider; sends signed IPN callbacks." {
            tags "External"
        }
        smtp = softwareSystem "SMTP Server (P1 - optional)" "Delivers email only when P1 notifications are selected and SMTP is configured." {
            tags "Optional"
        }

        guest -> shop "Uses REST API to browse products, register and log in" "HTTP/JSON"
        customer -> shop "Uses REST API for authentication, own profile, checkout, order history and payment URLs" "HTTP/JSON"
        staff -> shop "Uses REST API for order queue, details and fulfillment transitions" "HTTP/JSON"
        admin -> shop "Uses REST API for products/images, stock, roles, orders and reconciliation" "HTTP/JSON"
        customer -> vnpay "Initiates payment in browser using the signed URL" "HTTPS"
        vnpay -> shop "Sends payment notification / IPN callback" "Signed provider callback"
        shop -> smtp "Sends email when P1 is enabled" "SMTP" {
            tags "Optional"
        }

        guest -> backend "Browses catalog, registers and logs in" "REST, HTTP/JSON"
        customer -> backend "Manages own account/orders; requests payment URL; follows browser return" "REST / browser return, HTTP"
        staff -> backend "Views order queue/details and advances permitted fulfillment states" "REST, JWT"
        admin -> backend "Manages products/images, audited stock and roles; manages orders and reads reconciliation" "REST, JWT"
        backend -> database "Reads/writes business data atomically" "TypeORM, SQL"
        backend -> files "Stores and serves product images" "Filesystem I/O"
        vnpay -> backend "Sends verified, idempotently handled IPN" "Signed provider callback"
        backend -> smtp "Sends email if P1 enabled" "SMTP" {
            tags "Optional"
        }

        auth -> database "Persists accounts and refresh sessions" "TypeORM"
        users -> database "Reads/updates profiles and audited roles" "TypeORM"
        users -> auth "Revokes refresh families on password change" "In-process call"
        products -> database "Reads/writes catalog and image references" "TypeORM"
        products -> files "Stores/reads images; cleans orphan uploads" "Filesystem I/O"
        inventory -> database "Adjusts/reserves/releases stock atomically" "TypeORM, transactions"
        orders -> inventory "Reserves stock; releases on cancellation/expiry" "In-process collaboration"
        orders -> database "Persists orders, snapshots and history" "TypeORM, transactions"
        payments -> database "Persists attempts and settles eligible orders" "TypeORM, transactions"
        vnpay -> payments "Sends IPN for signature/data verification" "Signed provider callback"
        expiration -> payments "Runs safe attempt expiry" "In-process call"
        expiration -> orders "Runs order expiry and stock release" "In-process call"
        categories -> database "Reads/writes categories if selected" "TypeORM" {
            tags "Optional"
        }
        cart -> database "Reads/writes own cart if selected" "TypeORM" {
            tags "Optional"
        }
        notifications -> database "Persists/claims events and delivery outcomes" "TypeORM" {
            tags "Optional"
        }
        notifications -> smtp "Sends after commit; recovers/retries eligible events" "SMTP" {
            tags "Optional"
        }
    }

    views {
        systemContext shop "SystemContext" {
            title "E-commerce Backend API - System Context"
            include *
            autoLayout lr
        }

        container shop "Containers" {
            title "E-commerce Backend API - Containers"
            include *
            autoLayout lr
        }

        component backend "BackendComponents" {
            title "Backend Application - Component Diagram (P0)"
            include auth users products inventory orders payments expiration health database files vnpay
            autoLayout lr 500 250
        }

        component backend "BackendOptionalComponents" {
            title "Backend Application - Optional Logical Components (P1)"
            include categories cart notifications database smtp
            autoLayout lr
        }

        styles {
            element "Person" {
                shape Person
                background #08427B
                color #FFFFFF
            }
            element "Software System" {
                background #666666
                color #FFFFFF
            }
            element "Container" {
                background #438DD5
                color #FFFFFF
            }
            element "Backend" {
                background #1168BD
            }
            element "Component" {
                background #D6E8FA
                color #12395B
            }
            element "External" {
                background #666666
                color #FFFFFF
                width 400
                height 200
            }
            element "Database" {
                shape Cylinder
            }
            element "FileStorage" {
                shape Folder
            }
            element "Optional" {
                background #FFF3CD
                color #5C4400
                border dashed
            }
            relationship "Relationship" {
                color #555555
            }
            relationship "Optional" {
                dashed true
            }
        }
    }
}
